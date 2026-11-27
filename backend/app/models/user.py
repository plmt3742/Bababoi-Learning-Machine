"""账号表（05 §5.2 users）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, TimestampMixin, utcnow


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
    # 偏好的最后写入时间单独记：TimestampMixin.updated_at 会因为登录写 last_login_at
    # 被 onupdate 刷新，设置页的"最近更新"会在每次登录后跳变。
    # 建号即有值（= 建号时间），迁移老行由 c8e1b6a4d902 回填；接口仍留 created_at 兜底。
    preference_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=utcnow
    )
    # BE-028：token 版本号，JWT 的 `ver` 声明必须与它一致才放行。
    # 只在"全踢"动作时 +1：改密（BE-029）、未来的管理员强制下线。
    # 登录、登出都**不**动它——学生手机拍题 + 电脑做题，登录就 +1 会互相踢下线
    # （定案单 2026-11-21 §3）；登出只清前端 token。
    # 老 token 没有 `ver` 声明，按 0 处理：部署后旧 token 在用户改密前仍然有效。
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
