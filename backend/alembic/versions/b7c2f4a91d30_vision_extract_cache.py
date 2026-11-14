"""vision_extract_cache: BE-024 识图结果缓存

Revision ID: b7c2f4a91d30
Revises: c8e1b6a4d902
Create Date: 2026-11-12

版本链：`#58`（BE-026）的 `c8e1b6a4d902` 已先合入 main，本迁移接在它后面，
避免与 main 出现两个 head。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7c2f4a91d30"
down_revision: str | None = "c8e1b6a4d902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vision_extract_cache",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("image_sha", sa.String(length=16), nullable=False),
        sa.Column("subject_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("hop1_version", sa.String(length=32), nullable=False),
        sa.Column("hop2_version", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "has_incomplete", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint(
            "user_id",
            "image_sha",
            "subject_key",
            "hop1_version",
            "hop2_version",
            name="uq_vision_cache_key",
        ),
    )
    op.create_index(
        "ix_vision_extract_cache_user_id", "vision_extract_cache", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_vision_extract_cache_user_id", table_name="vision_extract_cache")
    op.drop_table("vision_extract_cache")
