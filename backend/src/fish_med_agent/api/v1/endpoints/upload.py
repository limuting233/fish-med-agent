from fastapi import APIRouter, Depends, File, Request, UploadFile

from fish_med_agent.api.deps import get_current_user_id
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.schemas.upload import (
    DeleteImageRequest,
    DeleteImageResponse,
    UploadImageResponse,
)
from fish_med_agent.service.upload_service import UploadService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/image", response_model=ApiResponse[UploadImageResponse])
async def upload_image(
        http_request: Request,
        file: UploadFile = File(..., description="待上传的图片文件"),
        current_user_id: int = Depends(get_current_user_id),
):
    """
    上传单张图片到 MinIO 对象存储。

    限制：
    - 类型：jpg / png / webp / gif（按 magic number 校验，不信 Content-Type）
    - 大小：最大 10MB
    - 鉴权：必须携带有效 access token

    Returns:
        UploadImageResponse:
            object_key / content_type / extension / size / original_filename
    """
    request_id = getattr(http_request.state, "request_id")
    upload_service = UploadService()
    response = await upload_service.upload_image(current_user_id, file)
    return success_response(
        request_id=request_id,
        data=response,
    )


@router.delete("/image", response_model=ApiResponse[DeleteImageResponse])
async def delete_image(
        http_request: Request,
        body: DeleteImageRequest,
        current_user_id: int = Depends(get_current_user_id),
):
    """
    删除单张图片（按 object_key）。

    - object_key：上传接口返回的那个 key，必须在 images/ 目录下
    - 鉴权：必须携带有效 access token
    - 对象不存在返回 404；key 非法返回 400

    Returns:
        DeleteImageResponse:
            - object_key: 被删除的 object_key
    """
    request_id = getattr(http_request.state, "request_id")
    upload_service = UploadService()
    deleted_key = await upload_service.delete_image(current_user_id, body.object_key)
    return success_response(
        request_id=request_id,
        data=DeleteImageResponse(object_key=deleted_key),
    )
