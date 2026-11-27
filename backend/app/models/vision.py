"""识图任务（B 档：提交拿单号 + 轮询取结果，05 §6.8）。

为什么不复用 `generation_task`：它的 `question_id` 是非空外键，而识图发生在
"题目还没创建"之前；新表纯新增，可整表回滚。

`active_slot`：每人同时只允许 1 个未完成任务。active 时存 user_id、终态置 NULL，
靠唯一约束（SQLite/MySQL 都允许多行 NULL）堵死"先查后插"的竞态。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, utcnow

# queued | running | done | failed | canceled —— 与 generation_task 同一套词表
VISION_JOB_ACTIVE_STATUSES = ("queued", "running")
VISION_JOB_TERMINAL_STATUSES = ("done", "failed", "canceled")


class VisionJob(Base):
    __tablename__ = "vision_job"
    __table_args__ = (
        Index("ix_vjob_status_created", "status", "created_at"),  # claim FIFO
        Index("ix_vjob_user_status", "user_id", "status"),  # 每人 active 查询
        Index("ix_vjob_expires", "expires_at"),  # 过期清理扫描
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    force_refresh: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 每人同时只允许 1 个未完成任务：active 存 user_id，终态置 NULL。
    # 用与 user_id 同宽的 BIGINT（MySQL 上 INTEGER 会溢出/类型不一致）。
    active_slot: Mapped[int | None] = mapped_column(
        BigIntPK, nullable=True, unique=True
    )

    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
