from fastapi import APIRouter, Depends, File, Request, UploadFile

from fish_med_agent.api.deps import get_current_user_id
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.response import ApiResponse, success_response
from fish_med_agent.schemas.upload import UploadImageResponse
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
    上传图片到 MinIO 对象存储。

    限制：
    - 类型：jpg / png / webp / gif（按 magic number 校验，不信 Content-Type）
    - 大小：单张最大 10MB
    - 鉴权：必须携带有效 access token

    Returns:
        UploadImageResponse:
            - object_key: 对象存储 key，形如 images/yyyy/mm/dd/{uuid}.{ext}
            - content_type: 服务端按 magic number 检测出的 MIME，例如 image/jpeg
            - extension: 文件扩展名，例如 jpg
            - size: 文件大小（字节）
            - original_filename: 客户端上传时的原始文件名（可能为 null）
    """
    request_id = getattr(http_request.state, "request_id")
    upload_service = UploadService()
    result = await upload_service.upload_image(current_user_id, file)
    return success_response(
        request_id=request_id,
        data=result,
    )
