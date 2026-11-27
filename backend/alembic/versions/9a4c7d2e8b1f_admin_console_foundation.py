"""admin 管理端地基：角色/禁用/审计/密码申请/告警确认

Revision ID: 9a4c7d2e8b1f
Revises: d6b8c2e4f901
Create Date: 2026-11-28

ADM-002 / ADM-009 / BE-030（28 号文档 §6、ADR-009）。
- `users` 增加 role / disabled_at / disabled_reason / must_change_password /
  temp_password_expires_at；role 历史行进前向迁移默认 student，管理员只由 seed 创建。
- `admin_audit_logs` 只追加；不建外键，actor/target 存快照。
- `password_reset_requests` 未命中用户名不建单，对外固定 202。
- `admin_alert_acks` 只存「已确认」，告警本身实时推导。

降级直接删表/删列；密码申请与审计都是新数据，没有历史行需要合并。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9a4c7d2e8b1f"
down_revision: str | None = "d6b8c2e4f901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'student'"),
            )
        )
        batch_op.add_column(sa.Column("disabled_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("disabled_reason", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column("temp_password_expires_at", sa.DateTime(), nullable=True)
        )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("target_label", sa.String(length=128), nullable=True),
        sa.Column("target_owner_id", sa.Integer(), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False, server_default="success"),
        sa.Column("request_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("ip", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"]
    )
    op.create_index(
        "ix_admin_audit_actor_created",
        "admin_audit_logs",
        ["actor_user_id", "created_at"],
    )
    op.create_index(
        "ix_admin_audit_action_created",
        "admin_audit_logs",
        ["action", "created_at"],
    )
    op.create_index(
        "ix_admin_audit_target", "admin_audit_logs", ["target_type", "target_id"]
    )

    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("submitted_email", sa.String(length=128), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.String(length=255), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("delivery_channel", sa.String(length=16), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_password_reset_requests_created_at",
        "password_reset_requests",
        ["created_at"],
    )
    op.create_index(
        "ix_password_reset_status_created",
        "password_reset_requests",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_password_reset_user_created",
        "password_reset_requests",
        ["user_id", "created_at"],
    )

    op.create_table(
        "admin_alert_acks",
        sa.Column("alert_key", sa.String(length=32), primary_key=True),
        sa.Column("acknowledged_by", sa.String(length=32), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("admin_alert_acks")
    op.drop_index("ix_password_reset_user_created", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_status_created", table_name="password_reset_requests")
    op.drop_index(
        "ix_password_reset_requests_created_at", table_name="password_reset_requests"
    )
    op.drop_table("password_reset_requests")
    op.drop_index("ix_admin_audit_target", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_action_created", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_actor_created", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("temp_password_expires_at")
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("disabled_reason")
        batch_op.drop_column("disabled_at")
        batch_op.drop_column("role")
