from datetime import datetime, timezone, timedelta

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.core.config import settings
from fish_med_agent.core.exception import UsernameOrPasswordError, UserNotFoundError, InvalidRefreshTokenError
from fish_med_agent.core.logging import get_logger
from fish_med_agent.core.security import verify_password, create_token, decode_token
from fish_med_agent.models import User
from fish_med_agent.repositories.user_repo import UserRepo

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._user_repo = UserRepo(db)

    async def login(self, username: str, password: str) -> dict:
        # 根据用户名获取用户,检查用户是否存在,如果不存在则返回错误信息
        exist_user = await self._user_repo.get_by_username(username)
        if not exist_user or not verify_password(password, exist_user.password):
            logger.warning(f"{username}: username or password is incorrect")
            raise UsernameOrPasswordError()

        exist_user.last_login_at = datetime.now(timezone.utc)

        exist_user = await self._user_repo.update(exist_user)

        # 生成access token 和 refresh token
        return self._create_access_refresh_token(exist_user.id)

    async def get_me(self, user_id: int) -> User:
        """
        获取当前登录用户信息
        Args:
            user_id: 用户ID

        Returns:
            User: 用户对象
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"user_id={user_id} not found or inactive")
            raise UserNotFoundError()
        return user

    def _create_access_refresh_token(self, user_id: int)->dict:
        """
        根据用户ID生成一对 access token 和 refresh token

        用于登录成功和 refresh token 轮换两个场景, 内部辅助方法,
        调用方需自行确保 user_id 已通过身份校验。

        Args:
            user_id: 已通过校验的用户ID, 会作为 JWT payload 的 sub 字段

        Returns:
            dict: 包含以下字段的字典
                - access_token (str): 短期访问令牌, 有效期为 ACCESS_TOKEN_EXPIRE_MINUTES 分钟
                - refresh_token (str): 长期刷新令牌, 有效期为 REFRESH_TOKEN_EXPIRE_DAYS 天
        """
        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return {
            "access_token": {
                "value": create_token(
                    user_id=user_id,
                    token_type="access",
                    expires_delta=access_expires,
                ),
                "expires_in": access_expires,
                "type": "bearer",

            },
            "refresh_token": {
                "value": create_token(
                    user_id=user_id,
                    token_type="refresh",
                    expires_delta=refresh_expires,
                ),
                "expires_in": refresh_expires,
            }
        }

    async def refresh(self, refresh_token: str) -> dict:
        """
        凭 refresh token 轮换签发新的 access/refresh token 对

        Args:
            refresh_token: 从 HttpOnly Cookie 中取出的旧 refresh token

        Returns:
            dict: 新的 access_token 和 refresh_token

        Raises:
            InvalidRefreshTokenError: token 过期/签名错误/类型错误/用户不存在或被禁用
        """
        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            logger.debug("refresh token expired")
            raise InvalidRefreshTokenError()
        except jwt.PyJWTError as e:
            logger.debug(f"decode refresh token failed: {e}")
            raise InvalidRefreshTokenError()

        if payload.get("type") != "refresh":
            logger.warning(f"unexpected token type for refresh: {payload.get('type')}")
            raise InvalidRefreshTokenError()

        sub = payload.get("sub")
        if not sub:
            raise InvalidRefreshTokenError()
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            raise InvalidRefreshTokenError()

        # 防"用户被删/禁用但 token 仍在有效期"
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"refresh: user_id={user_id} not found or inactive")
            raise InvalidRefreshTokenError()

        return self._create_access_refresh_token(user.id)

