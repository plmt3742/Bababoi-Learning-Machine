"""vision_extract_cache: 补 model + last_forced_at（BE-024 缓存出口）

Revision ID: c4e8a1d62f37
Revises: b7c2f4a91d30
Create Date: 2026-11-12

`b7c2f4a91d30` 已经推过，不能就地改它：跑过旧版的人会停在同一个 revision 却没有新列。
这里用一条前向迁移补齐——加 `model` / `last_forced_at`，并把唯一键扩成含 `model`。
SQLite 不能直接改约束，走 batch（重建表）；MySQL 上就是 ADD COLUMN + DROP/ADD UNIQUE。
降级会把"同图同版本、不同 model"的重复行合并成最新一行，否则缩回 5 列唯一键时撞键。

`b7c2f4a91d30` 已接在 `c8e1b6a4d902` 后面；本文件跟着它走，不用动。

2026-11-27 例外：本条就地改了 MySQL 分支（`batch.drop_constraint` 在 MySQL 上找不到被反射成
index 的唯一键）。安全前提只有两条：① MySQL 上没有库能通过旧版——旧版正是在这里挂的；
② SQLite 分支逐字符未变，schema 产物与旧版完全一致。MySQL 上线后若再发现迁移问题，
**必须新开一条前向迁移，不许再就地改本条**。
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


def _is_mysql() -> bool:
    return op.get_bind().dialect.name == "mysql"


def upgrade() -> None:
    if _is_mysql():
        # MySQL 把 UNIQUE KEY 反射成 unique Index，batch.drop_constraint(type_="unique")
        # 在它身上找不到；而且 MySQL 本来就能直接 ADD COLUMN / DROP+ADD UNIQUE。
        op.add_column(
            "vision_extract_cache",
            sa.Column("model", sa.String(length=64), nullable=False, server_default=""),
        )
        op.add_column(
            "vision_extract_cache", sa.Column("last_forced_at", sa.DateTime(), nullable=True)
        )
        op.drop_index("uq_vision_cache_key", table_name="vision_extract_cache")
        op.create_unique_constraint("uq_vision_cache_key", "vision_extract_cache", _UNIQUE_V2)
        return
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
    if _is_mysql():
        op.drop_index("uq_vision_cache_key", table_name="vision_extract_cache")
        op.create_unique_constraint("uq_vision_cache_key", "vision_extract_cache", _UNIQUE_V1)
        op.drop_column("vision_extract_cache", "last_forced_at")
        op.drop_column("vision_extract_cache", "model")
        return
    with op.batch_alter_table("vision_extract_cache", recreate="always") as batch:
        batch.drop_constraint("uq_vision_cache_key", type_="unique")
        batch.create_unique_constraint("uq_vision_cache_key", _UNIQUE_V1)
        batch.drop_column("last_forced_at")
        batch.drop_column("model")
