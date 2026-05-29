from pydantic import BaseModel, Field


class UploadImageResponse(BaseModel):
    """
    图片上传响应。
    """

    object_key: str = Field(..., description="对象存储中的 key")
    content_type: str = Field(..., description="文件 MIME 类型，例如 image/jpeg")
    extension: str = Field(..., description="文件扩展名，例如 jpg")
    size: int = Field(..., description="文件大小，单位字节")
    original_filename: str | None = Field(None, description="客户端上传时的原始文件名")
