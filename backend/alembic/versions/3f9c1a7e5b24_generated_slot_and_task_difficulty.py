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

    _backfill_target_index()


def _backfill_target_index() -> None:
    """给历史生成题回填 1/2/3 格位（前端意见单 §六-1）。

    不回填的话老题的 target_index 全是 NULL：详情页排序落到 coalesce 兜底、
    前端还得再按 created_at 兜一层，等于同一件事两个地方各猜一次。
    按 `parent_question_id, created_at, id` 的顺序编号，正好等于旧版"一次生成 3 道"
    的插入顺序，也就是用户当时看到的顺序。
    只有活跃行参与（软删的历史组不是用户看到的三张卡），超过 3 条的留 NULL 而不是编出 4、5 格。

    逐行 UPDATE 而不是相关子查询：MySQL 8 禁止"UPDATE 的表同时出现在子查询里"
    （error 1093），这里要 SQLite/MySQL 一份代码跑得过。老库行数本来就是题数×3 的量级。
    """
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, parent_question_id FROM generated_questions "
        "WHERE deleted_at IS NULL ORDER BY parent_question_id, created_at, id"
    )).fetchall()
    seen: dict[int, int] = {}
    for row_id, parent_id in rows:
        seen[parent_id] = seen.get(parent_id, 0) + 1
        slot = seen[parent_id]
        if slot <= 3:
            bind.execute(
                sa.text("UPDATE generated_questions SET target_index = :slot WHERE id = :id"),
                {"slot": slot, "id": row_id},
            )


def downgrade() -> None:
    with op.batch_alter_table('generation_task', schema=None) as batch_op:
        batch_op.drop_column('difficulty')

    with op.batch_alter_table('generated_questions', schema=None) as batch_op:
        batch_op.drop_index('ix_generated_parent_slot')
        batch_op.drop_column('target_index')
