"""vision_extract_cache: 补 model + last_forced_at（BE-024 缓存出口）

Revision ID: c4e8a1d62f37
Revises: b7c2f4a91d30
Create Date: 2026-11-12

`b7c2f4a91d30` 已经推过，不能就地改它：跑过旧版的人会停在同一个 revision 却没有新列。
这里用一条前向迁移补齐——加 `model` / `last_forced_at`，并把唯一键扩成含 `model`。
SQLite 不能直接改约束，走 batch（重建表）；MySQL 上就是 ADD COLUMN + DROP/ADD UNIQUE。

⚠️ 合并顺序：`#58` 的 `c8e1b6a4d902` 与 `b7c2f4a91d30` 同父。若 #58 先合，只改
`b7c2f4a91d30` 的 `down_revision` 为 `c8e1b6a4d902`，本文件不用动。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4e8a1d62f37"
down_revision: str | None = "b7c2f4a91d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UNIQUE_V2 = ["user_id", "image_sha", "subject_key", "model", "hop1_version", "hop2_version"]
_UNIQUE_V1 = ["user_id", "image_sha", "subject_key", "hop1_version", "hop2_version"]


def upgrade() -> None:
    with op.batch_alter_table("vision_extract_cache", recreate="always") as batch:
        batch.add_column(
            sa.Column("model", sa.String(length=64), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("last_forced_at", sa.DateTime(), nullable=True))
        batch.drop_constraint("uq_vision_cache_key", type_="unique")
        batch.create_unique_constraint("uq_vision_cache_key", _UNIQUE_V2)


def downgrade() -> None:
    with op.batch_alter_table("vision_extract_cache", recreate="always") as batch:
        batch.drop_constraint("uq_vision_cache_key", type_="unique")
        batch.create_unique_constraint("uq_vision_cache_key", _UNIQUE_V1)
        batch.drop_column("last_forced_at")
        batch.drop_column("model")
