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
