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


class ConversationService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._conversation_repo = ConversationRepo(db)

    async def get_list(self, current_user_id: int) -> list[dict]:
        """
        获取用户的所有对话
        Args:
            current_user_id: 当前用户ID

        Returns:
            对话列表
        """
        res = await self._conversation_repo.list(current_user_id)
        return [r.to_dict() for r in res]
