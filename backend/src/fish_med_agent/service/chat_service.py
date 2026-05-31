import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.agents import SYSTEM_PROMPT, dispatch_tool_call, openai_tools_schema
from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger
from fish_med_agent.models import Conversation
from fish_med_agent.repositories.conversation_repo import ConversationRepo
from fish_med_agent.schemas.chat import ChatRequest, ImageInput, VideoInput
from fish_med_agent.service.video_service import VideoDescription, video_service
from fish_med_agent.service.vision_service import vision_service

logger = get_logger(__name__)

# tool-use 循环最大迭代次数，防止 LLM 无限调用工具
_MAX_TOOL_ITERATIONS = 8

# 注入给 rag_search 的对话历史最大轮数（1 轮 = 1 user + 1 assistant）
_RAG_HISTORY_MAX_TURNS = 6

# 需要注入 conversation_history 的工具名集合
_TOOLS_NEEDING_HISTORY = {"rag_search"}


class ChatService:

    def __init__(self, db: AsyncSession):
        self._db = db
        self._async_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.DEEPSEEK_TIMEOUT,
        )
        self._conversation_repo = ConversationRepo(db)

    async def generate_stream_response(
        self, chat_request: ChatRequest, current_user_id: int
    ) -> AsyncGenerator[str, None]:
        """生成带 tool-use 循环的流式响应。

        SSE 事件类型：
        - start: 响应开始
        - vision.start / vision.done: 图片识别开始/结束（仅带图时） {count}
        - video.start / video.done: 视频识别开始/结束（仅带视频时） {count}
        - message.delta: 文本内容增量 {content}
        - tool.call: 工具调用开始 {tool_call_id, name, arguments}
        - tool.result: 工具调用完成 {tool_call_id, name, ok, error?}
        - done: 响应正常结束
        - error: 响应失败 {message}
        """
        conversation_id = chat_request.conversation_id
        message = chat_request.message

        exist_conversation = await self._conversation_repo.get_by_id(conversation_id)
        now = _now_iso()
        if not exist_conversation:
            new_conversation = Conversation(
                title=message.content[:10],
                user_id=current_user_id,
                messages=[],
                metadata_={},
            )
            exist_conversation = await self._conversation_repo.add(new_conversation)

        logger.info(
            f"chat start: conv={exist_conversation.id} "
            f"images={len(message.images or [])} videos={len(message.videos or [])}"
        )

        try:
            yield _sse(event="start")

            # 前置 transform：若带图或视频，先并行跑 vision 把媒体转描述拼进 content
            # —— 后续 tool-use 循环里 DeepSeek 只看到融合后的纯文本
            user_content = message.content
            image_descs: list[str] = []
            video_descs: list[VideoDescription] = []

            if message.images or message.videos:
                if message.images:
                    yield _sse(
                        event="vision.start",
                        data={"count": len(message.images)},
                    )
                if message.videos:
                    yield _sse(
                        event="video.start",
                        data={"count": len(message.videos)},
                    )

                # 图片描述 + 视频帧描述并行；都受 VisionService 全局 Semaphore 节流
                image_descs, video_descs = await asyncio.gather(
                    vision_service.describe_images(message.images or []),
                    video_service.describe_videos(message.videos or []),
                )
                user_content = _merge_media_descriptions(
                    message.content,
                    list(message.images or []),
                    image_descs,
                    list(message.videos or []),
                    video_descs,
                )

                if message.images:
                    yield _sse(
                        event="vision.done",
                        data={"count": len(message.images)},
                    )
                if message.videos:
                    yield _sse(
                        event="video.done",
                        data={"count": len(message.videos)},
                    )

            # 追加本轮用户消息；用 + 拼新 list 以触发 SQLAlchemy dirty 检测
            user_msg: dict[str, Any] = {
                "role": "user",
                "content": user_content,
                "created": now,
            }
            if message.images:
                # 原始图片元数据单独存，便于前端回放原图
                user_msg["images"] = [img.model_dump() for img in message.images]
            if message.videos:
                user_msg["videos"] = [v.model_dump() for v in message.videos]
            messages = exist_conversation.messages + [user_msg]
            logger.info(f"history_len after user msg appended: {len(messages)}")

            for iteration in range(_MAX_TOOL_ITERATIONS):
                logger.info(f"tool-use iteration {iteration + 1}/{_MAX_TOOL_ITERATIONS}")

                # 拼请求载荷：system + 历史（剔除 created 字段）
                payload_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                    _strip_message(m) for m in messages
                ]

                content_buf = ""
                tool_calls_buf: dict[int, dict[str, Any]] = {}
                finish_reason: str | None = None

                resp_stream = await self._async_client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=payload_messages,
                    tools=openai_tools_schema(),
                    temperature=settings.DEEPSEEK_TEMPERATURE,
                    extra_body={"thinking": {"type": "disabled"}},
                    stream=True,
                )

                async for chunk in resp_stream:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta

                    if delta.content:
                        content_buf += delta.content
                        yield _sse(event="message.delta", data={"content": delta.content})

                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            _accumulate_tool_call(tool_calls_buf, tc_delta)

                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                # 流结束：根据 finish_reason 决定继续工具循环还是结束
                if tool_calls_buf:
                    tool_calls = [tool_calls_buf[i] for i in sorted(tool_calls_buf)]

                    # 追加 assistant 消息（带 tool_calls）
                    messages = messages + [
                        {
                            "role": "assistant",
                            "content": content_buf or "",
                            "tool_calls": tool_calls,
                            "created": _now_iso(),
                        }
                    ]

                    # 通知前端工具开始执行
                    for tc in tool_calls:
                        yield _sse(
                            event="tool.call",
                            data={
                                "tool_call_id": tc["id"],
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        )

                    # 抽取最近 N 轮 user/assistant 对话，供需要历史的工具使用
                    rag_history = _build_rag_history(messages, _RAG_HISTORY_MAX_TURNS)

                    # 并行执行所有工具
                    results = await asyncio.gather(
                        *[
                            dispatch_tool_call(
                                tc["function"]["name"],
                                tc["function"]["arguments"],
                                context=(
                                    {"conversation_history": rag_history}
                                    if tc["function"]["name"] in _TOOLS_NEEDING_HISTORY
                                    else None
                                ),
                            )
                            for tc in tool_calls
                        ]
                    )

                    # 追加 tool 结果消息 + 通知前端
                    tool_messages = []
                    for tc, result in zip(tool_calls, results):
                        tool_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": json.dumps(result, ensure_ascii=False),
                                "created": _now_iso(),
                            }
                        )
                        yield _sse(
                            event="tool.result",
                            data={
                                "tool_call_id": tc["id"],
                                "name": tc["function"]["name"],
                                "ok": "error" not in result,
                                "error": result.get("error"),
                                "result": result,
                            },
                        )
                    messages = messages + tool_messages
                    # 继续下一轮，让 LLM 基于工具结果生成最终答案
                    continue

                # 没有 tool_calls：本轮是最终答案
                messages = messages + [
                    {"role": "assistant", "content": content_buf, "created": _now_iso()}
                ]
                logger.info(f"chat done: finish_reason={finish_reason}")
                break
            else:
                # for-else：循环耗尽未 break，说明触发了上限
                logger.warning(f"hit max tool iterations ({_MAX_TOOL_ITERATIONS})")
                yield _sse(
                    event="error",
                    data={"message": "工具调用次数超限，请重新发起对话"},
                )
                await self._db.rollback()
                return

            # 持久化
            exist_conversation.metadata_ = {"last_message_at": _now_iso()}
            exist_conversation.messages = messages
            await self._conversation_repo.update(exist_conversation)
            await self._db.commit()
            yield _sse(event="done")

        except Exception:
            logger.exception("chat stream failed")
            await self._db.rollback()
            yield _sse(event="error", data={"message": "模型响应失败，请稍后重试"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_rag_history(
    messages: list[dict[str, Any]], max_turns: int
) -> list[dict[str, str]]:
    """从完整 messages 抽取最近 max_turns 轮 user/assistant 对话。

    - 跳过纯 tool_calls 的 assistant 消息（无正文）
    - 跳过 role=tool 的工具结果消息
    - 只保留 LightRAG 需要的 {role, content} 两个字段
    - 1 轮 = 1 user + 1 assistant 消息
    """
    clean: list[dict[str, str]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant"):
            continue
        if not content:  # 跳过 content 为空（如纯 tool_calls 的 assistant）
            continue
        clean.append({"role": role, "content": content})
    # 1 轮 = 2 条消息
    return clean[-2 * max_turns:]


_NON_LLM_FIELDS = {"created", "images", "videos"}


def _strip_message(msg: dict[str, Any]) -> dict[str, Any]:
    """从存储的消息里剔除 LLM 不需要的字段（如 created / images）。

    保留 role / content / tool_calls / tool_call_id 等 OpenAI 协议字段。
    `images` 是我们自己持久化用的元数据，DeepSeek 不认，必须剥掉；
    图片相关信息已经在拼 content 时由 vision 描述合并进去了。
    """
    return {k: v for k, v in msg.items() if k not in _NON_LLM_FIELDS}


def _merge_media_descriptions(
    text: str,
    images: list[ImageInput],
    image_descs: list[str],
    videos: list[VideoInput],
    video_descs: list[VideoDescription],
) -> str:
    """把 vision 转出来的图/视频描述拼到用户原文后面。

    格式：
        <原文>

        [用户附图]
        图1 (gill.jpg)：xxx
        图2：xxx

        [用户附视频]
        视频1 (swim.mp4, 时长 12.0s)：
          帧1 (2.0s)：xxx
          帧2 (6.0s)：xxx
          帧3 (10.0s)：xxx

    描述若为 "[图片识别失败：...]" / "[视频识别失败：...]" 也照样拼进去，
    让 DeepSeek 感知到"识别失败"并引导用户文字补充。
    """
    if not images and not videos:
        return text

    parts: list[str] = [text]

    if images:
        parts.append("")
        parts.append("[用户附图]")
        for i, (img, desc) in enumerate(zip(images, image_descs), start=1):
            name_tag = f" ({img.original_filename})" if img.original_filename else ""
            parts.append(f"图{i}{name_tag}：{desc}")

    if videos:
        parts.append("")
        parts.append("[用户附视频]")
        for i, (vid, vd) in enumerate(zip(videos, video_descs), start=1):
            head = f"{vid.original_filename}, " if vid.original_filename else ""
            parts.append(
                f"视频{i} ({head}时长 {vid.duration_seconds:.1f}s)："
            )
            for frame in vd.frames:
                parts.append(f"  帧 ({frame.ts_sec:.1f}s)：{frame.text}")

    return "\n".join(parts)


def _accumulate_tool_call(buf: dict[int, dict[str, Any]], tc_delta: Any) -> None:
    """把流式 tool_call delta 按 index 累积成完整结构。"""
    idx = tc_delta.index
    if idx not in buf:
        buf[idx] = {
            "id": "",
            "type": "function",
            "function": {"name": "", "arguments": ""},
        }
    entry = buf[idx]
    if tc_delta.id:
        entry["id"] = tc_delta.id
    if tc_delta.function:
        if tc_delta.function.name:
            entry["function"]["name"] = tc_delta.function.name
        if tc_delta.function.arguments:
            entry["function"]["arguments"] += tc_delta.function.arguments


def _sse(event: str, data: Any | None = None) -> str:
    if not event or "\n" in event or "\r" in event:
        raise ValueError("SSE event must be a non-empty single-line string")
    payload = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"
