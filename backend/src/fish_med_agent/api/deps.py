from typing import AsyncGenerator

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.core.exception import InvalidTokenError
from fish_med_agent.core.logging import get_logger
from fish_med_agent.core.security import decode_token
from fish_med_agent.db.session import AsyncSessionLocal

logger = get_logger(__name__)

# auto_error=False: 缺失/格式错误时不抛 FastAPI 默认 403, 由我们抛 InvalidTokenError
bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    :return:异步数据库会话
    """
    async with AsyncSessionLocal() as session:
        yield session


def get_current_user_id(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """
    从 Authorization: Bearer <access_token> 中解析并返回当前用户ID。

    Args:
        credentials: 由 HTTPBearer 解析出的认证信息, 缺失时为 None

    Returns:
        当前用户ID

    Raises:
        InvalidTokenError: token 缺失、格式错误、过期、签名无效, 或不是 access 类型
    """

    if not credentials or credentials.scheme.lower() != "bearer":
        logger.debug("Authorization header missing or not Bearer scheme")
        raise InvalidTokenError()

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        logger.debug("access token expired")
        raise InvalidTokenError(message="token 已过期")
    except jwt.PyJWTError as e:
        logger.debug(f"decode access token failed: {e}")
        raise InvalidTokenError()

    # 只接受 access token, 防止用 refresh token 直接访问业务接口
    if payload.get("type") != "access":
        logger.debug(f"unexpected token type: {payload.get('type')}")
        raise InvalidTokenError()

    sub = payload.get("sub")

    if not sub:
        raise InvalidTokenError()

    try:
        return int(sub)
    except (TypeError, ValueError):
        logger.warning(f"invalid sub in token: {sub!r}")
        raise InvalidTokenError()




