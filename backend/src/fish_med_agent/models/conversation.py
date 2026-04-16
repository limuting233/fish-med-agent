
from typing import Any

from sqlalchemy import String, BIGINT
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fish_med_agent.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="会话标题")
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False, index=True, comment="所属用户主键ID")
    summary: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, comment="会话摘要")
    messages: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True, comment="回话记录")
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True, comment="会话元数据")
