from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    :return:异步数据库会话
    """
    async with AsyncSessionLocal() as session:
        yield session


def get_current_user_id() -> int:
    """
    获取当前用户ID
    Returns:
        当前用户ID

    """

    return 1
