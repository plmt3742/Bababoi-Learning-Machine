"""users.token_version：服务端可吊销的会话版本号

Revision ID: b3c7d9e1f204
Revises: e9b1c7f3a2d5
Create Date: 2026-11-19 21:40:00.000000

BE-028。JWT 是无状态的，签发后在有效期内无法失效（只有换 JWT_SECRET 能一次踢掉所有人）。
这一列让 token 带上版本号：登录 / 登出 / 改密时 +1，校验时版本不一致即 401。
新增列走前向迁移；老 token 没有 `ver` 声明按 0 处理，所以部署本身不会把在线用户踢下线，
要等他们下次登录（版本变成 1）旧 token 才会失效。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b3c7d9e1f204'
down_revision: str | None = 'e9b1c7f3a2d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOT NULL + server_default：历史行在迁移时就拿到 0，不靠代码兜默认值；
    # SQLite 与 MySQL 8 用同一套 DDL（batch 会按方言重建/加列）
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('token_version', sa.Integer(), nullable=False, server_default=sa.text('0'))
        )


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('token_version')
