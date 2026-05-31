from pydantic import BaseModel, ConfigDict, Field, model_validator


# 单条消息附带媒体的总件数上限（图 + 视频 合计）
# 设为 6 是因为 vision 调用预算最敏感的是"图片张数"那条路径，6 张相当于一个 LLM
# 上下文里能塞进的合理上限；视频会被抽帧但帧数固定 3，单独计算
MAX_MEDIA_PER_MESSAGE = 6

# 每个视频固定抽 3 帧（首/中/尾）。如改动要同步 video_service 实现
VIDEO_FRAMES_PER_CLIP = 3


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


class VideoInput(BaseModel):
    """用户消息附带的单个视频。

    字段与 `POST /upload/video` 返回的 UploadVideoResponse 对齐——前端可直接透传。
    后端用 object_key 从 MinIO 取视频字节 → ffmpeg 抽 N 帧 → 复用 vision pipeline。
    """

    object_key: str = Field(..., min_length=1, description="MinIO object_key，必须在 videos/ 前缀下")
    content_type: str = Field(
        ...,
        description="MIME 类型",
        pattern=r"^video/(mp4|webm|quicktime)$",
    )
    extension: str = Field(..., description="文件扩展名，如 mp4 / webm / mov")
    size: int = Field(..., ge=0, description="文件大小，单位字节")
    duration_seconds: float = Field(
        ..., gt=0, description="视频时长，秒。上传时 ffmpeg.probe 测得"
    )
    original_filename: str | None = Field(
        default=None, description="客户端上传时的原始文件名，可空"
    )


class Message(BaseModel):
    """单条用户消息。"""

    content: str = Field(..., min_length=1, description="消息文本内容")
    images: list[ImageInput] | None = Field(
        default=None,
        description="附带的图片列表",
    )
    videos: list[VideoInput] | None = Field(
        default=None,
        description="附带的视频列表",
    )

    @model_validator(mode="after")
    def _check_total_media(self) -> "Message":
        total = len(self.images or []) + len(self.videos or [])
        if total > MAX_MEDIA_PER_MESSAGE:
            raise ValueError(
                f"images + videos 件数合计不能超过 {MAX_MEDIA_PER_MESSAGE}，当前为 {total}"
            )
        return self


class ChatRequest(BaseModel):
    """聊天请求模型。"""

    conversation_id: int = Field(..., description="会话ID")
    message: Message = Field(..., description="用户消息")

    model_config = ConfigDict(extra="forbid")
