"""管理端数据模型（28 号文档 §6 / ADR-009）。

三张表分开建模、集中在这个模块：
- `admin_audit_logs`：只追加，管理员所有写操作与敏感读取都要落一条；
- `password_reset_requests`：学生线上申请 → 管理员审批；
- `admin_alert_acks`：告警「已确认」状态，告警本身由真实数据实时推导，不存表。

审计里的 actor/target 都存快照（用户名/标签），改名或删号后历史仍可读。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, utcnow


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_admin_audit_actor_created", "actor_user_id", "created_at"),
        Index("ix_admin_audit_action_created", "action", "created_at"),
        Index("ix_admin_audit_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # 管理员删号后审计仍要能看：不建外键，只留快照
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_username: Mapped[str] = mapped_column(
        String(32), nullable=False, default="", server_default=""
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 不同目标的 id 形态不同（用户数字 id、任务单号），统一按字符串存
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(
        String(16), nullable=False, default="success", server_default="success"
    )
    request_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", server_default=""
    )
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    user_agent: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", server_default=""
    )
    # append-only：不挂 TimestampMixin 的 updated_at，避免给人"日志可修改"的错觉
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"
    __table_args__ = (
        Index("ix_password_reset_status_created", "status", "created_at"),
        Index("ix_password_reset_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # 未命中用户名不建单（对外固定 202），所以 user_id 一定有值
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    user_agent: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", server_default=""
    )
    # 临时密码过期时间；通过/重新生成时写
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 学生用临时密码成功改密后回写，用于排查「临时密码是否被用过」
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )


class AdminAlertAck(Base):
    __tablename__ = "admin_alert_acks"

    alert_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    acknowledged_by: Mapped[str] = mapped_column(String(32), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
