from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from fish_med_agent.api.deps import get_db
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.auth import LoginRequest
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.service.auth_service import AuthService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=ApiResponse[dict[str, str]])
async def login(
        http_request: Request,
        login_request: LoginRequest,
        db: AsyncSession = Depends(get_db),
):
    """
    登录接口
    Args:
        http_request: HTTP请求对象, 用于获取请求状态
        login_request: 登录请求
        db: 异步数据库会话, 用于执行数据库操作, 从依赖项中获取
    Returns:

    """
    logger.debug(f"Received login request: {login_request}")
    auth_service = AuthService(db)
    request_id = getattr(http_request.state, "request_id")
    token_dict = await auth_service.login(login_request.username, login_request.password)
    return success_response[dict[str, Any]](
        request_id=request_id,
        data=token_dict,
    )
