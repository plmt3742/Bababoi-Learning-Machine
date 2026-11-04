"""错题主表与标签（05 §5.2 questions / tags / question_tags）。

`options` 与 `blanks` 存 JSON，形状由 app/schemas/question.py 定义并在写入前校验——
数据库这边不做结构约束，因为 SQLite 与 MySQL 的 JSON 校验能力不对等（05 §5.3）。
"""
from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, SoftDeleteMixin, TimestampMixin


class Question(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=False, index=True
    )

    subject: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    chapter: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="text"
    )  # text | image

    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    answer_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    question_type: Mapped[str] = mapped_column(String(16), nullable=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blanks: Mapped[list | None] = mapped_column(JSON, nullable=True)

    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mastery_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unmastered", index=True
    )  # unmastered | reviewing | mastered
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="confirmed"
    )  # MVP 恒为 confirmed，删除靠 deleted_at

    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crop_box: Mapped[list | None] = mapped_column(JSON, nullable=True)
    crop_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    tags: Mapped[list[Tag]] = relationship(
        secondary="question_tags", back_populates="questions"
    )


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", "type"),)  # 05 §5.2 tags 的唯一约束

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="knowledge_point"
    )  # knowledge_point | custom

    questions: Mapped[list[Question]] = relationship(
        secondary="question_tags", back_populates="tags"
    )


class QuestionTag(Base):
    """错题与标签的多对多关联；复合主键天然去重。"""

    __tablename__ = "question_tags"
    __table_args__ = (Index("ix_question_tags_tag", "tag_id"),)

    question_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("questions.id"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("tags.id"), primary_key=True
    )
