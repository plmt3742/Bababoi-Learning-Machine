"""user_ai_settings + ai_call_logs.key_source（BE-020 / ADR-007）

Revision ID: e9b1c7f3a2d5
Revises: c4e8a1d62f37
Create Date: 2026-11-14

- 新表 `user_ai_settings`：每用户一行，Key 只存 Fernet 密文 + 末四位
- `ai_call_logs.key_source`：这次调用用的是 user 还是 system 的 Key
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e9b1c7f3a2d5"
down_revision: str | None = "c4e8a1d62f37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "user_ai_settings",
        sa.Column("user_id", _BIGINT, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=False),
        sa.Column("key_last4", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_ai_settings_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_ai_settings")),
    )
    op.create_index(
        op.f("ix_user_ai_settings_created_at"), "user_ai_settings", ["created_at"]
    )
    with op.batch_alter_table("ai_call_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("key_source", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ai_call_logs", schema=None) as batch_op:
        batch_op.drop_column("key_source")
    op.drop_index(op.f("ix_user_ai_settings_created_at"), table_name="user_ai_settings")
    op.drop_table("user_ai_settings")
