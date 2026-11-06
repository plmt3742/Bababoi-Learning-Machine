"""账号表（05 §5.2 users）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # BE-026（issue #44）：生成的相似题是否必须与原题同题型。**默认开启**是产品决策，
    # 所以用 NOT NULL + server_default，历史用户在迁移时就拿到 1，不靠代码里兜默认值——
    # 那样会让"没读过偏好的老代码"和"读过偏好的新代码"给出不同结果。
    # 出现第二项偏好时再抽 user_settings 表；BYOK 的 user_ai_settings 是密钥表，不混进来。
    enforce_same_question_type: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
