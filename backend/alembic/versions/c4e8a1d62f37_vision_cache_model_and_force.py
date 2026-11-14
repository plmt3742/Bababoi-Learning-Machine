"""vision_extract_cache: 补 model + last_forced_at（BE-024 缓存出口）

Revision ID: c4e8a1d62f37
Revises: b7c2f4a91d30
Create Date: 2026-11-12

`b7c2f4a91d30` 已经推过，不能就地改它：跑过旧版的人会停在同一个 revision 却没有新列。
这里用一条前向迁移补齐——加 `model` / `last_forced_at`，并把唯一键扩成含 `model`。
SQLite 不能直接改约束，走 batch（重建表）；MySQL 上就是 ADD COLUMN + DROP/ADD UNIQUE。
降级会把"同图同版本、不同 model"的重复行合并成最新一行，否则缩回 5 列唯一键时撞键。

`b7c2f4a91d30` 已接在 `c8e1b6a4d902` 后面；本文件跟着它走，不用动。
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
    # 唯一键缩回 5 列时，同图同版本但 model 不同的两行会撞键：先合并，保留最新一行。
    # 派生表包一层，MySQL 才允许在 DELETE 里读同一张表。
    op.execute(
        sa.text(
            "DELETE FROM vision_extract_cache WHERE id NOT IN ("
            " SELECT keep_id FROM ("
            "  SELECT MAX(id) AS keep_id FROM vision_extract_cache"
            "  GROUP BY user_id, image_sha, subject_key, hop1_version, hop2_version"
            " ) AS keep"
            ")"
        )
    )
    with op.batch_alter_table("vision_extract_cache", recreate="always") as batch:
        batch.drop_constraint("uq_vision_cache_key", type_="unique")
        batch.create_unique_constraint("uq_vision_cache_key", _UNIQUE_V1)
        batch.drop_column("last_forced_at")
        batch.drop_column("model")
