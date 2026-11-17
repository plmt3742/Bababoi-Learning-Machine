"""练习记录业务（BE-012）：创建（防重复）+ 查询。

05 §6.4 只定了端点和字段，「防重复」的口径这里落实为：
同用户、同生成题、同答案、同判定，在 60 秒窗口内的再次提交视为
重复点击（02-goals 验收「重复点击不会创建重复数据」），返回 409。
窗口外允许重复——隔天重练同一题是正常使用，不能挡。
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models import GeneratedQuestion, PracticeRecord
from app.schemas.practice import DUPLICATE_WINDOW_SECONDS, PracticeRecordCreate


def _owned_generated(session: Session, user_id: int, generated_question_id: int) -> None:
    """生成题必须存在、属于当前用户且未删除；否则一律 404，不区分原因。"""
    row = session.get(GeneratedQuestion, generated_question_id)
    if (
        row is None
        or row.user_id != user_id
        or row.deleted_at is not None
    ):
        raise ApiError(ErrorCode.NOT_FOUND, "生成题不存在", 404)


def create(
    session: Session, user_id: int, data: PracticeRecordCreate
) -> PracticeRecord:
    _owned_generated(session, user_id, data.generated_question_id)

    window_start = utcnow() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    dup = session.scalar(
        select(PracticeRecord.id).where(
            PracticeRecord.user_id == user_id,
            PracticeRecord.generated_question_id == data.generated_question_id,
            PracticeRecord.user_answer == data.user_answer,
            PracticeRecord.is_correct == data.is_correct,
            PracticeRecord.created_at >= window_start,
        )
    )
    if dup is not None:
        raise ApiError(ErrorCode.PRACTICE_DUPLICATE, "相同作答刚提交过，请勿重复点击", 409)

    record = PracticeRecord(
        user_id=user_id,
        generated_question_id=data.generated_question_id,
        user_answer=data.user_answer,
        is_correct=data.is_correct,
        duration_seconds=data.duration_seconds,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_records(
    session: Session,
    user_id: int,
    page: int,
    page_size: int,
    generated_question_id: int | None = None,
) -> tuple[list[PracticeRecord], int]:
    """新→旧分页；generated_question_id 为附加过滤（05 未列，前端练习页要用）。"""
    conditions = [PracticeRecord.user_id == user_id]
    if generated_question_id is not None:
        conditions.append(
            PracticeRecord.generated_question_id == generated_question_id
        )
    total = session.scalar(select(func.count()).select_from(PracticeRecord).where(*conditions))
    rows = session.scalars(
        select(PracticeRecord)
        .where(*conditions)
        .order_by(PracticeRecord.created_at.desc(), PracticeRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total
