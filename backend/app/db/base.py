"""ORM 基类：命名约定 + 跨库主键类型 + 时间戳/软删除字段。

命名约定必须统一，否则 Alembic 在 SQLite 上生成的约束名与 MySQL 上不一致，
迁移到生产库时会变成一堆「无法重命名约束」的手工活。
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# MySQL 用 BIGINT，SQLite 的自增只对 INTEGER 生效（05 §5.3「自增」那条）
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """UTC naive。用 Python 侧默认值而不是 server_default，SQLite 与 MySQL 才给得出同一个值。"""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    """时间一律存 UTC naive，展示时 +8（05 §5.2 表头约定）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )


class SoftDeleteMixin:
    """删除一律软删除；统计与列表默认过滤 deleted_at IS NULL（05 §5.3）。"""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
