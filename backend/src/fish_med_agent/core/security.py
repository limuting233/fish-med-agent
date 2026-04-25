from datetime import timedelta, timezone, datetime

import jwt
from pwdlib import PasswordHash

from fish_med_agent.core.config import settings

password_hash = PasswordHash.recommended()  # 使用推荐的密码哈希算法


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    Args:
        password: 密码字符串

    Returns:、
        哈希后的密码字符串
    """
    return password_hash.hash(password)


def verify_password(plain_password, hashed_password) -> bool:
    """
    验证密码是否匹配
    Args:
        plain_password: 明文密码字符串
        hashed_password: 哈希后的密码字符串

    Returns:、
        如果密码匹配则返回True, 否则返回False
    """
    return password_hash.verify(plain_password, hashed_password)


def create_token(*, user_id: int, token_type: str, expires_delta: timedelta):
    """
    创建JWT令牌
    Args:
        user_id: 用户ID
        token_type: 令牌类型
        expires_delta: 过期时间, 从当前时间开始计算

    Returns:
        JWT令牌字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码JWT令牌
    Args:
        token: JWT令牌字符串

    Returns:
        解码后的JWT令牌字典
    """
    return jwt.decode(token, key=settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
