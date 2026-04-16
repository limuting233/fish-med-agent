from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from fish_med_agent.core.config import settings

# 创建异步数据库引擎
async_engine: AsyncEngine = create_async_engine(
    url=settings.postgres_async_url,
    echo=settings.ECHO_SQL,  # 是否打印SQL语句
    pool_size=settings.POOL_SIZE,  # 连接池大小
    max_overflow=settings.MAX_OVERFLOW,  # 超过连接池大小后的最大连接数
    pool_pre_ping=True,  # 连接池是否在每次取出连接前进行检查,如果连接已断开,则会重新连接
    pool_timeout=settings.POOL_TIMEOUT,  # 连接池获取连接的超时时间,单位为秒
    pool_recycle=settings.POOL_RECYCLE,  # 连接池连接的最大空闲时间,单位为秒,超过该时间,连接会被回收
    pool_use_lifo=True,  # 连接池是否使用LIFO(Last In First Out)策略,如果为True,则最近使用的连接会被优先返回
)
