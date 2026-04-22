from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class Message(BaseModel):
    """
    消息模型
    """
    content: str = Field(..., min_length=1, description="消息内容")
    images: list[str] | None = Field(default=None, description="用户图片URL列表")


class ChatRequest(BaseModel):
    """
    聊天请求模型
    """
    conversation_id: int = Field(..., description="会话ID")

    message: Message = Field(..., description="用户消息字典")

    model_config = ConfigDict(
        extra="forbid",
    )
