from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.models import User


class UserRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_username(self, username: str) -> User | None:
        """
        根据用户名获取用户
        Args:
            username:

        Returns:
            User | None: 用户对象, 如果用户存在则返回用户对象, 否则返回None

        """

        stmt = (
            select(User)
            .where(
                User.username == username,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )

        res = await self._db.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, user: User) -> User:
        """
        更新用户
        Args:
            user: 用户对象

        Returns:
            User: 更新后的用户对象
        """
        await self._db.merge(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user
