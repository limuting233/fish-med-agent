from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from fish_med_agent.models.base import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="昵称", default=None)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True, comment="邮箱",
                                              default=None)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True, comment="手机号",
                                              default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None,
                                                           comment="最后登录时间")
