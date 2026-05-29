from fastapi import APIRouter, Depends, File, Request, UploadFile

from fish_med_agent.api.deps import get_current_user_id
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.schemas.upload import UploadImagesResponse
from fish_med_agent.service.upload_service import UploadService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/images", response_model=ApiResponse[UploadImagesResponse])
async def upload_image(
        http_request: Request,
        files: list[UploadFile] = File(..., description="待上传的图片文件，最多 6 张"),
        current_user_id: int = Depends(get_current_user_id),
):
    """
    批量上传图片到 MinIO 对象存储。

    限制：
    - 数量：一次 1~6 张（multipart 里用同一个字段名 `files` 重复传多个文件）
    - 类型：jpg / png / webp / gif（按 magic number 校验，不信 Content-Type）
    - 大小：单张最大 10MB
    - 鉴权：必须携带有效 access token

    任一张校验/上传失败则整批失败（已写入的不回滚）。

    Returns:
        UploadImagesResponse:
            - images: 上传结果列表，顺序与上传顺序一致，每项含
              object_key / content_type / extension / size / original_filename
    """
    request_id = getattr(http_request.state, "request_id")
    upload_service = UploadService()
    images = await upload_service.upload_images(current_user_id, files)
    return success_response(
        request_id=request_id,
        data=UploadImagesResponse(images=images),
    )
