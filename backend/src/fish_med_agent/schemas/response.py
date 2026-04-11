from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    API响应模型
    """
    code: int = 200
    message: str = "success"
    request_id: str
    data: T


def success_response(*, request_id: str, data: T) -> ApiResponse[T]:
    """
    成功响应
    Args:
        request_id: 请求ID
        data: 响应数据

    Returns:
        成功响应对象

    """
    return ApiResponse[T](
        request_id=request_id,
        data=data,
    )
