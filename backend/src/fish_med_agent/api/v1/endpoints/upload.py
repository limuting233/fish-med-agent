from fastapi import APIRouter, Depends, File, Request, UploadFile

from fish_med_agent.api.deps import get_current_user_id
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.schemas.upload import (
    DeleteImageRequest,
    DeleteImageResponse,
    PresignRequest,
    PresignResponse,
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


@router.post("/image/presign", response_model=ApiResponse[PresignResponse])
async def presign_image_urls(
        http_request: Request,
        body: PresignRequest,
        current_user_id: int = Depends(get_current_user_id),
):
    """
    批量为已有 object_key 生成 presigned URL，供历史会话回显图片用。

    - object_keys：上传接口返回过的 key 列表，最多 50 个
    - 非法 key（不在 images/ 目录下）会从结果中省略，前端按缺失处理
    - **不校验对象是否存在**：节省一轮 RTT；图片若已被删，前端 <img onerror> 兜底
    - URL 默认有效期 1 小时（与 access_token 同步）

    Returns:
        PresignResponse:
            urls: dict[object_key, url]
            expires_in: URL 有效秒数
    """
    request_id = getattr(http_request.state, "request_id")
    upload_service = UploadService()
    urls, expires_at = await upload_service.generate_presigned_urls(body.object_keys)
    logger.info(
        f"user {current_user_id} presigned {len(urls)}/{len(body.object_keys)} keys"
    )
    return success_response(
        request_id=request_id,
        data=PresignResponse(urls=urls, expires_at=expires_at),
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
