from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from fish_med_agent.db.engine import async_engine

# 创建异步数据库会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 是否在提交事务后过期会话,如果为True,则在提交事务后,会话中的所有对象都会过期,需要重新查询数据库
    autoflush=False,  # 是否自动刷新会话,将未提交的更改写入数据库,但不提交事务
    autocommit=False,  # 是否自动提交事务
)
