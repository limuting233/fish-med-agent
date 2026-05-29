from pydantic import BaseModel, Field


class UploadImageItem(BaseModel):
    """
    单张图片上传结果。
    """

    object_key: str = Field(..., description="对象存储中的 key")
    content_type: str = Field(..., description="文件 MIME 类型，例如 image/jpeg")
    extension: str = Field(..., description="文件扩展名，例如 jpg")
    size: int = Field(..., description="文件大小，单位字节")
    original_filename: str | None = Field(None, description="客户端上传时的原始文件名")


class UploadImagesResponse(BaseModel):
    """
    批量图片上传响应。
    """

    images: list[UploadImageItem] = Field(..., description="上传成功的图片列表，顺序与上传顺序一致")
