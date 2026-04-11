from fastapi import APIRouter, Request

from fish_med_agent.core.config import settings
from fish_med_agent.schemas.response import success_response, ApiResponse

router = APIRouter()


@router.get("/healthz", response_model=ApiResponse[dict[str, str]])
async def healthz(request: Request) -> ApiResponse[dict[str, str]]:
    """
    健康检查接口
    Args:
        request: 请求对象

    Returns:
        健康检查响应对象

    """
    request_id = getattr(request.state, "request_id")  # 从请求状态中获取请求ID
    return success_response(
        request_id=request_id,
        data={
            "status": "ok",
            "service": settings.SERVICE_NAME,
            "service_version": settings.SERVICE_VERSION,
            "api_version": settings.API_VERSION,

        },
    )
