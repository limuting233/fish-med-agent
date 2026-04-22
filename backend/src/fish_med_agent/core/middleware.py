import uuid
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from fish_med_agent.core.logging import get_logger, reset_request_id, set_request_id

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        处理请求ID中间件
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            响应对象
        """
        request_id = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex}"  # 生成请求ID
        request.state.request_id = request_id
        request_id_token = set_request_id(request_id)
        start_time = perf_counter()

        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception(
                    "Request failed: {method} {path}",
                    method=request.method,
                    path=request.url.path,
                )
                raise

            response.headers["X-Request-Id"] = request_id
            duration_ms = (perf_counter() - start_time) * 1000
            logger.info(
                "Request completed: {method} {path} {status_code} {duration_ms:.2f}ms",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        finally:
            reset_request_id(request_id_token)
