from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.core.config import settings
from fish_med_agent.core.exception import UsernameOrPasswordError
from fish_med_agent.core.logging import get_logger
from fish_med_agent.core.security import verify_password, create_token
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

        # 生成token
        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_dict={
            "access_token": create_token(
                user_id=exist_user.id,
                token_type="access",
                expires_delta=access_expires,
            ),
            "refresh_token": create_token(
                user_id=exist_user.id,
                token_type="refresh",
                expires_delta=refresh_expires,
            ),
            "token_type": "Bearer",
            "expires_in": int(access_expires.total_seconds()),
        }
        return token_dict
