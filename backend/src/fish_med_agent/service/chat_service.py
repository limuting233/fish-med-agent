import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger
from fish_med_agent.models import Conversation
from fish_med_agent.repositories.conversation_repo import ConversationRepo
from fish_med_agent.schemas.chat import ChatRequest

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "你是一个面向水产养殖场景的鱼病问答助手。"
    "请基于用户描述给出可能病因、需要补充确认的信息、处置建议和风险提示。"
    "不能替代兽医或水产专家现场诊断，遇到高风险情况要建议联系专业人员。"
)


class ChatService:

    def __init__(self, db: AsyncSession):
        self._db = db
        self._async_client = AsyncOpenAI(
            api_key=settings.CLOSEAI_API_KEY,
            base_url=settings.CLOSEAI_BASE_URL,
            timeout=settings.CLOSEAI_TIMEOUT,
        )
        self._conversation_repo = ConversationRepo(db)

    async def generate_stream_response(self, chat_request: ChatRequest, current_user_id: int) -> AsyncGenerator[
        str, None]:
        """
        生成聊天流响应
        Args:
            chat_request: 聊天请求
            current_user_id: 当前用户ID

        Returns:
            聊天流响应

        """

        conversation_id = chat_request.conversation_id  # conversation_id 会话ID
        message = chat_request.message  # message 用户消息

        # 根据conversation_id,判断该会话是否存在，如果不存在则添加一个新的会话
        exist_conversation = await self._conversation_repo.get_by_id(conversation_id)
        now = datetime.now(timezone.utc).isoformat()
        if not exist_conversation:
            # 创建新的conversation
            new_conversation = Conversation(
                title=message.content[:10],
                user_id=current_user_id,
                messages=[],
                metadata_={
                    "conversation_created_at": now,
                },
            )
            exist_conversation = await self._conversation_repo.add(new_conversation)

        # 在已经存在的messages基础上，添加本次请求的message，作为新的messages
        messages = exist_conversation.messages + [{"role": "user", "content": message.content, "created": now}]

        logger.info(f"messages length: {len(messages)}")

        # 这里需要计算一下messages的token数，不能超过所使用模型的token数的80%
        # todo 计算messages的token数
        try:
            yield self._sse(event="start", data={})
            resp_stream = await self._async_client.chat.completions.create(
                model=settings.CLOSEAI_MODEL,
                messages=[{"role": "system", "content": _SYSTEM_PROMPT}] +
                         [{"role": msg["role"], "content": msg["content"]} for msg in messages],
                temperature=settings.CLOSEAI_TEMPERATURE,
                stream=True,
            )

            assistant_content = ""

            async for chunk in resp_stream:
                if not chunk.choices:
                    continue

                delta_content = chunk.choices[0].delta.content
                if not delta_content:
                    continue

                assistant_content += delta_content

                yield self._sse(event="message.delta", data={"content": delta_content})

            # 成功后保存 user + assistant 消息，更新 last_message_at，commit 到数据库
            now = datetime.now(timezone.utc).isoformat()
            messages.append({"role": "assistant", "content": assistant_content, "created": now})
            exist_conversation.metadata_["last_message_at"] = now
            exist_conversation.messages = messages
            await self._conversation_repo.update(exist_conversation)
            await self._db.commit()
            yield self._sse(event="done", data={})

        except Exception as e:
            logger.exception("chat stream failed")
            await self._db.rollback()
            yield self._sse(event="error", data={"message": "模型响应失败，请稍后重试"})

    @staticmethod
    def _sse(event: str = "message.delta", data: Any | None = None) -> str:
        if not event or "\n" in event or "\r" in event:
            raise ValueError("SSE event must be a non-empty single-line string")

        payload = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {payload}\n\n"
