from datetime import datetime, timezone
from sqlalchemy import BIGINT, DateTime, Identity
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base model for all models
    """

    # 主键ID：自增整数,唯一标识每个记录,默认从1开始自增
    id: Mapped[int] = mapped_column(BIGINT, Identity(start=1), primary_key=True, comment="主键ID")
    # 创建时间：插入时由数据库自动写入，utc时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 default=lambda: datetime.now(timezone.utc), comment="创建时间")

    # 更新时间：插入时写入，更新时自动刷新，utc时间
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc), comment="更新时间")

    # 软删除时间：未删除为 NULL，删除时写入时间
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None,
                                                        index=True, comment="软删除时间")
