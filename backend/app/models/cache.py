"""识图结果缓存（BE-024 / 05 §6.8）。

同一张图（文件名是内容寻址的 sha16）+ 同一个 subject + 同一组两跳 prompt 版本，
输入完全相同；缓存它省的是 17–90s 的一次重跑，演示重传/重试直接命中。

只缓存「两跳成功且有题」的结果（含 `incomplete`）：失败不缓存（重试是用户合法动作），
空结果不缓存（更可能是传错图，钉死一次误操作没意义）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, utcnow


class VisionExtractCache(Base):
    __tablename__ = "vision_extract_cache"
    __table_args__ = (
        # 键=用户 + 图内容 + 学科 + 两跳版本；版本变了自然不命中，不用手动清表
        UniqueConstraint(
            "user_id",
            "image_sha",
            "subject_key",
            "hop1_version",
            "hop2_version",
            name="uq_vision_cache_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=False, index=True
    )
    image_sha: Mapped[str] = mapped_column(String(16), nullable=False)
    # 空串而不是 NULL：MySQL 唯一索引里 NULL 互不相等，留 NULL 等于"没选学科的图永不命中"
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    hop1_version: Mapped[str] = mapped_column(String(32), nullable=False)
    hop2_version: Mapped[str] = mapped_column(String(32), nullable=False)

    # 存最终出参（KB 级），不存第 1 跳那 6000–17000 token 的转录中间产物
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_incomplete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
