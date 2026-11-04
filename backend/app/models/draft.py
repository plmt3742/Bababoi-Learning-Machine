"""录入草稿（05 §5.2 draft；PRD 5.2.4 服务端账户级草稿）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, utcnow


class Draft(Base):
    """每账号只有一份草稿，靠 user_id 唯一约束保证（PRD 5.2.4）。

    冲突解决用 `version` 乐观锁，不用 updated_at 比大小——浏览器时钟不可信，
    跨设备比较时间戳会把新内容当旧的覆盖掉。
    """

    __tablename__ = "draft"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=False
    )
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
