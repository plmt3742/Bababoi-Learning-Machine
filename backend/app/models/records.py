"""练习记录与 AI 调用日志（05 §5.2 practice_records / ai_call_logs）。"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, TimestampMixin
from app.models.generation import GeneratedQuestion
from app.models.question import Question
from app.models.user import User


class PracticeRecord(Base, TimestampMixin):
    """一次作答流水。错题的掌握状态写在 `questions.mastery_status`，不在这里。"""

    __tablename__ = "practice_records"
    __table_args__ = (
        Index("ix_practice_user_created", "user_id", "created_at"),
        Index("ix_practice_generated", "generated_question_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=False)
    generated_question_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("generated_questions.id"), nullable=False
    )
    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    generated_question: Mapped[GeneratedQuestion] = relationship(lazy="selectin")


class AiCallLog(Base, TimestampMixin):
    """PRD 5.5 的耗时埋点。`queue_wait_ms` 是入队到开始执行的排队时长。

    数值范围（duration 0–3600、token 数非负）由 schema 层校验，不落 DB CHECK——
    05 §5.3 要求 SQLite 与 MySQL 用同一套 DDL，CHECK 的表达能力两边不对等。
    """

    __tablename__ = "ai_call_logs"
    __table_args__ = (Index("ix_ai_call_stage_status", "operation", "status"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=True
    )
    question_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("questions.id"), nullable=True
    )

    operation: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # vision | analyze | generate | judge
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # BE-026：这一格按"题型必须一致"（strict）还是"允许换题型"（soft）校验。
    # 记在日志里而不是只记在代码路径里，是因为"默认开启值不值"这个问题只能靠
    # 按策略分组统计失败率来回答——没有这一列就量不出来。非 quiz 操作为 null。
    type_policy: Mapped[str | None] = mapped_column(String(16), nullable=True)

    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queue_wait_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False)  # success|error|invalid
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped[Question | None] = relationship(lazy="selectin")
    user: Mapped[User | None] = relationship(lazy="selectin")
