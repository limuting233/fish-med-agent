import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger
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

    async def generate_stream_response(self, chat_request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        生成聊天流响应
        Args:
            chat_request: 聊天请求

        Returns:
            聊天流响应

        """

        conversation_id = chat_request.conversation_id  # conversation_id 会话ID
        message = chat_request.message  # message 用户消息

        # 根据conversation_id去查询该会话的所有messages

        # 在已经存在的messages基础上，添加本次请求的message，作为新的messages
        logger.info(f"messages length: 2")
        try:
            resp_stream = await self._async_client.chat.completions.create(
                model=settings.CLOSEAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": _SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": message.content,
                    },
                ],
                temperature=settings.CLOSEAI_TEMPERATURE,
                stream=True,
            )

            async for chunk in resp_stream:
                if not chunk.choices:
                    continue

                delta_content = chunk.choices[0].delta.content
                if not delta_content:
                    continue

                yield self._sse(event="message.delta", data={"content": delta_content})

        except Exception as e:
            pass

    @staticmethod
    def _sse(event: str = "message.delta", data: Any | None = None) -> str:
        if not event or "\n" in event or "\r" in event:
            raise ValueError("SSE event must be a non-empty single-line string")

        payload = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {payload}\n\n"
