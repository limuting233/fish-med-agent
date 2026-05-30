from pydantic import BaseModel, ConfigDict, Field


# 单条消息最多附带的图片数（防止滥用 + 控制 vision 调用成本）
MAX_IMAGES_PER_MESSAGE = 6


class ImageInput(BaseModel):
    """用户消息附带的单张图片。

    字段与 `POST /upload/image` 返回的 UploadImageResponse 完全对齐——
    前端把上传接口的 response 整体塞进 message.images 数组即可，无需挑字段。

    后端只用 `object_key` 从 MinIO 取原图，再以 base64 内联方式喂给 vision 模型；
    其余字段用于日志、前端回放、未来可能的审计。
    """

    object_key: str = Field(..., min_length=1, description="上传接口返回的 MinIO object_key")
    content_type: str = Field(
        ...,
        description="MIME 类型，如 image/jpeg",
        pattern=r"^image/(jpeg|png|webp|gif)$",
    )
    extension: str = Field(..., description="文件扩展名，如 jpg / png")
    size: int = Field(..., ge=0, description="文件大小，单位字节")
    original_filename: str | None = Field(
        default=None, description="客户端上传时的原始文件名，可空"
    )


class Message(BaseModel):
    """单条用户消息。"""

    content: str = Field(..., min_length=1, description="消息文本内容")
    images: list[ImageInput] | None = Field(
        default=None,
        description="附带的图片列表，最多 6 张",
        max_length=MAX_IMAGES_PER_MESSAGE,
    )


class ChatRequest(BaseModel):
    """聊天请求模型。"""

    conversation_id: int = Field(..., description="会话ID")
    message: Message = Field(..., description="用户消息")

    model_config = ConfigDict(extra="forbid")
