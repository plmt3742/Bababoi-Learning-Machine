"""生成题与后台任务（05 §5.2 generated_questions / generation_task）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, SoftDeleteMixin, TimestampMixin, utcnow


class GeneratedQuestion(Base, TimestampMixin, SoftDeleteMixin):
    """一道相似题。`answer_md` / `explanation_md` 对应 US-4 的「展开答案显示参考答案与简要思路」。"""

    __tablename__ = "generated_questions"
    __table_args__ = (
        Index("ix_generated_parent", "parent_question_id"),
        Index("ix_generated_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    parent_question_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("questions.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=False, index=True
    )

    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    answer_md: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_md: Mapped[str] = mapped_column(Text, nullable=False)

    question_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blanks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)

    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    validation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="valid"
    )  # valid | invalid | fallback
    validation_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class GenerationTask(Base):
    """队列任务记录，任务中心（FR-14）的数据源。

    「同一 question_id + stage + target_index 只允许一个 active task」这条约束
    故意不落库：MySQL 8 没有部分索引，落成唯一索引会把历史任务一起挡掉。
    它由 service 层在入队前检查（BE-006/007），这里只留查询用的复合索引。
    """

    __tablename__ = "generation_task"
    __table_args__ = (
        Index("ix_task_status_created", "status", "created_at"),
        Index("ix_task_question_stage", "question_id", "stage"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("questions.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=False, index=True
    )

    stage: Mapped[str] = mapped_column(String(16), nullable=False)  # analysis | quiz
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued"
    )  # queued | running | done | failed
    target_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
