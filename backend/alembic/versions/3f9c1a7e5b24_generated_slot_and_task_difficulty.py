"""generated question slot + task difficulty

Revision ID: 3f9c1a7e5b24
Revises: 7d155a41e345
Create Date: 2026-11-06 18:40:12.000000

ADR-006（三段并发生成）需要的两列，各自独立可回滚：
- generated_questions.target_index：这道题占三张卡里的哪一格
- generation_task.difficulty：这一段请求的难度档
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '3f9c1a7e5b24'
down_revision: str | None = '7d155a41e345'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('generated_questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target_index', sa.Integer(), nullable=True))
        # MySQL 8 不支持 CREATE INDEX IF NOT EXISTS，batch_op 会按名字查重；
        # 这里只加"父题 + 格子"的复合索引，单列查询仍走 ix_generated_parent
        batch_op.create_index(
            'ix_generated_parent_slot', ['parent_question_id', 'target_index'], unique=False
        )

    with op.batch_alter_table('generation_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('difficulty', sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('generation_task', schema=None) as batch_op:
        batch_op.drop_column('difficulty')

    with op.batch_alter_table('generated_questions', schema=None) as batch_op:
        batch_op.drop_index('ix_generated_parent_slot')
        batch_op.drop_column('target_index')
