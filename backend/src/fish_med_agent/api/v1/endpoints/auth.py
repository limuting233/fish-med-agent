from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.api.deps import get_db
from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.auth import LoginRequest
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.service.auth_service import AuthService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=ApiResponse[dict])
async def login(
        http_request: Request,
        http_response: Response,
        login_request: LoginRequest,
        db: AsyncSession = Depends(get_db),
):
    """
    登录接口
    Args:
        http_request: HTTP请求对象, 用于获取请求状态
        http_response: HTTP响应对象, 用于设置响应头
        login_request: 登录请求
        db: 异步数据库会话, 用于执行数据库操作, 从依赖项中获取
    Returns:

    """
    logger.debug(f"Received login request: {login_request}")
    auth_service = AuthService(db)
    request_id = getattr(http_request.state, "request_id")
    token_dict = await auth_service.login(login_request.username, login_request.password)

    refresh_token = token_dict.pop("refresh_token")
    logger.debug(f"Generated refresh token: {refresh_token}")
    http_response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 刷新token过期时间, 单位秒
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMEITE,
        path="/api/v1/auth/refresh",
    )
    return success_response(
        request_id=request_id,
        data=token_dict,
    )


@router.post("/refresh")
async def get_refresh_token(
        http_request: Request,
        http_response: Response,
):
    """
    重新获取refresh token接口
    Args:
        http_request: HTTP请求对象, 用于获取请求状态
        http_response: HTTP响应对象, 用于设置响应头

    Returns:
    """
