from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.models import Conversation


class ConversationRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, conversation_id: int) -> Conversation:
        """
        根据ID获取对话
        Args:
            conversation_id: 对话ID

        Returns:
            对话对象
        """
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.deleted_at.is_(None),
            )
        )

        res = await self._db.execute(stmt)
        return res.scalar_one_or_none()

    async def add(self, conversation: Conversation) -> Conversation:
        """
        添加对话
        Args:
            conversation: 对话对象

        Returns:

            添加的对话对象
        """
        self._db.add(conversation)
        await self._db.flush()
        await self._db.refresh(conversation)
        return conversation

    async def update(self, conversation: Conversation) -> Conversation:
        """
        更新对话
        Args:
            conversation: 对话对象

        Returns:
            更新后的对话对象
        """
        conversation = await self._db.merge(conversation)
        await self._db.flush()
        await self._db.refresh(conversation)
        return conversation

    async def list(self, user_id: int) -> list[Conversation]:
        """
        获取用户的所有对话
        Args:
            user_id: 用户ID

        Returns:
            对话列表
        """
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(
                Conversation.metadata_["last_message_at"]
                .as_string()
                .desc()
            )
        )
        res = await self._db.execute(stmt)
        return res.scalars().all()
