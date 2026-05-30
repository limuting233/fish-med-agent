from pydantic import BaseModel, Field


# 批量 presign 接口单次最多签的 URL 数（防滥用 + 控制响应体大小）
MAX_PRESIGN_BATCH = 50


class UploadImageResponse(BaseModel):
    """
    单张图片上传结果。
    """

    object_key: str = Field(..., description="对象存储中的 key")
    content_type: str = Field(..., description="文件 MIME 类型，例如 image/jpeg")
    extension: str = Field(..., description="文件扩展名，例如 jpg")
    size: int = Field(..., description="文件大小，单位字节")
    original_filename: str | None = Field(None, description="客户端上传时的原始文件名")
    url: str = Field(..., description="可直接 <img src> 访问的预签名 URL")
    url_expires_at: int = Field(
        ..., description="预签名 URL 的过期时间，UTC epoch 毫秒时间戳"
    )


class DeleteImageRequest(BaseModel):
    """
    删除单张图片请求。
    """

    object_key: str = Field(..., min_length=1, description="上传成功后返回的 object_key")


class DeleteImageResponse(BaseModel):
    """
    删除单张图片响应。
    """

    object_key: str = Field(..., description="被删除的 object_key")


class PresignRequest(BaseModel):
    """
    批量为已有 object_key 生成 presigned URL 的请求。

    典型场景：打开历史会话时，把会话里所有图片的 object_key 一次性发过来取 URL。
    """

    object_keys: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_PRESIGN_BATCH,
        description=f"待签名的 object_key 列表，最多 {MAX_PRESIGN_BATCH} 个",
    )


class PresignResponse(BaseModel):
    """
    批量 presign 响应。

    urls 是 dict 而非 list，保证乱序也能按 key 找到对应 URL；
    若某个 key 非法（不在 images/ 前缀下）会从结果中省略，前端按缺失处理即可。
    """

    urls: dict[str, str] = Field(..., description="object_key -> 预签名 URL")
    expires_at: int = Field(
        ..., description="所有 URL 的过期时间，UTC epoch 毫秒时间戳"
    )
