
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from fish_med_agent.api.deps import get_db, get_current_user_id
from fish_med_agent.core.config import settings
from fish_med_agent.core.exception import InvalidRefreshTokenError
# from fish_med_agent.core.exception import InvalidAccessTokenError,InvalidRefreshTokenError
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.auth import LoginRequest, UserInfoResponse
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

    access_token_dict = token_dict["access_token"]
    logger.debug(f"Generated access token: {access_token_dict["value"]}")

    refresh_token_dict = token_dict.pop("refresh_token")
    logger.debug(f"Generated refresh token: {refresh_token_dict["value"]}")

    http_response.set_cookie(
        key="refresh_token",
        value=refresh_token_dict["value"],
        httponly=True,
        max_age=int(refresh_token_dict["expires_in"].total_seconds()),  # refresh token过期时间, 单位秒
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMEITE,
        path=settings.refresh_token_cookie_path,
    )
    return success_response(
        request_id=request_id,
        data={
            "access_token": access_token_dict["value"],
            "token_type": access_token_dict["type"],
            "expires_at": int((access_token_dict["expires_in"] + datetime.now(timezone.utc)).timestamp() * 1000),
        },
    )


@router.get("/me", response_model=ApiResponse[UserInfoResponse])
async def get_me(
        http_request: Request,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
):
    """
    获取当前登录用户的信息
    Args:
        http_request: HTTP请求对象, 用于获取请求状态
        db: 异步数据库会话, 从依赖项中获取
        current_user_id: 当前用户ID, 从依赖项中获取

    Returns:
        当前用户信息
    """
    request_id = getattr(http_request.state, "request_id")
    auth_service = AuthService(db)
    user = await auth_service.get_me(current_user_id)
    return success_response(
        request_id=request_id,
        data=UserInfoResponse.model_validate(user),
    )


@router.post("/token/refresh")
async def refresh_token(
        http_request: Request,
        http_response: Response,
        db: AsyncSession = Depends(get_db),
):
    """
    重新获取access token 和 refresh token接口
    Args:
        http_request: HTTP请求对象, 用于获取请求状态
        http_response: HTTP响应对象, 用于设置响应头

    Returns:
    """
    request_id = getattr(http_request.state, "request_id")
    refresh_token = http_request.cookies.get("refresh_token")  # 获取 refresh token
    if not refresh_token:
        logger.debug("refresh_token cookie missing in request")
        raise InvalidRefreshTokenError()

    auth_service = AuthService(db)
    token_dict = await auth_service.refresh(refresh_token)

    new_access_token_dict = token_dict["access_token"]
    logger.debug(f"Generated new access token: {new_access_token_dict["value"]}")

    new_refresh_token_dict = token_dict.pop("refresh_token")
    logger.debug(f"Generated new refresh token: {new_refresh_token_dict["value"]}")

    http_response.set_cookie(
        key="refresh_token",
        value=new_refresh_token_dict["value"],
        httponly=True,
        max_age=int(new_refresh_token_dict["expires_in"].total_seconds()),  # refresh token过期时间, 单位秒
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMEITE,
        path=settings.refresh_token_cookie_path,
    )
    return success_response(
        request_id=request_id,
        data={
            "access_token": new_access_token_dict["value"],
            "token_type": new_access_token_dict["type"],
            "expires_at": int((new_access_token_dict["expires_in"] + datetime.now(timezone.utc)).timestamp() * 1000),
        },
    )
