"""用户自带的 AI Key（ADR-007 / 05 §6.9）。

一行对应一个用户；`api_key_ciphertext` 是 Fernet 密文，明文只存在于请求进来和调用
模型的那几毫秒里。`key_last4` 单独存，是为了 GET 时能返回 `sk-****abcd` 而不解密。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, TimestampMixin


class UserAiSettings(Base, TimestampMixin):
    __tablename__ = "user_ai_settings"

    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    # deepseek 留空走系统默认；openai_compatible 必须 https 且 host 在白名单里
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    key_last4: Mapped[str] = mapped_column(String(8), nullable=False)
