import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


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

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
