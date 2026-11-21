"""vision_job：识图任务化（提交 + 轮询）

Revision ID: d6b8c2e4f901
Revises: e9b1c7f3a2d5
Create Date: 2026-11-21

纯新增表，不动老表：识图改成"提交拿单号 → 轮询取结果"后，任务要在重启/多标签页
之间可恢复，且每人同时只能挂 1 个未完成任务（`active_slot` 可空唯一）。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd6b8c2e4f901'
down_revision: str | None = 'e9b1c7f3a2d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vision_job",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("image_path", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=32), nullable=True),
        sa.Column("force_refresh", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "active_slot",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("active_slot", name="uq_vision_job_active_slot"),
    )
    op.create_index("ix_vjob_status_created", "vision_job", ["status", "created_at"])
    op.create_index("ix_vjob_user_status", "vision_job", ["user_id", "status"])
    op.create_index("ix_vjob_expires", "vision_job", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_vjob_expires", table_name="vision_job")
    op.drop_index("ix_vjob_user_status", table_name="vision_job")
    op.drop_index("ix_vjob_status_created", table_name="vision_job")
    op.drop_table("vision_job")
