"""generation preferences: user toggle + call-log policy column

Revision ID: c8e1b6a4d902
Revises: 3f9c1a7e5b24
Create Date: 2026-11-07 03:40:12.000000

BE-026（issue #44）需要的两列，各自独立可回滚：
- users.enforce_same_question_type：题型一致性开关，默认开启。NOT NULL + server_default
  让历史用户在迁移时就拿到 1，不需要额外的 UPDATE 回填，也不依赖代码兜默认值。
- ai_call_logs.type_policy：quiz 段这次按 strict 还是 soft 校验，非 quiz 操作留 NULL。
  有了它才能按策略分组量"默认开启"的失败率；没有它这个问题只能靠猜。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c8e1b6a4d902'
down_revision: str | None = '3f9c1a7e5b24'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table：SQLite 不支持 ADD COLUMN NOT NULL 带默认值的常规写法，
    # 且 MySQL 8 那边 batch_op 会按名字查重，两边同一套 DDL（05 §5.3）
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'enforce_same_question_type',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('1'),
            )
        )
        # 偏好自己的写入时间；与 TimestampMixin.updated_at 分开，避免登录写
        # last_login_at 时把"最近更新"一起刷新。老行留 NULL，接口回退 created_at。
        batch_op.add_column(
            sa.Column('preference_updated_at', sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table('ai_call_logs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('type_policy', sa.String(length=16), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('ai_call_logs', schema=None) as batch_op:
        batch_op.drop_column('type_policy')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('preference_updated_at')
        batch_op.drop_column('enforce_same_question_type')
