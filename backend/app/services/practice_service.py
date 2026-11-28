"""练习记录业务（BE-012）：创建（防重复）+ 查询。

05 §6.4 只定了端点和字段，「防重复」的口径这里落实为：
同用户、同生成题、同答案、同判定，在 60 秒窗口内的再次提交视为
重复点击（02-goals 验收「重复点击不会创建重复数据」），返回 409。
窗口外允许重复——隔天重练同一题是正常使用，不能挡。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models import GeneratedQuestion, PracticeRecord, Question
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


# --- 今日待复习（#126 / 05 §6.5） -------------------------------------------------

DUE_LIMIT_DEFAULT = 6
DUE_LIMIT_MAX = 20

# 到期间隔按掌握度；契约单位是「天」，实现按滚动 24h（不是中国时区自然日）
DUE_REVIEW_DAYS: dict[str, int] = {"unmastered": 1, "reviewing": 3, "mastered": 7}
DUE_REASON_BY_STATUS: dict[str, str] = {
    "unmastered": "unmastered_1d",
    "reviewing": "reviewing_3d",
    "mastered": "mastered_7d",
}
# 排序口径 B：未练过 > 未掌握 > 复习中 > 已掌握；同档内最久未练优先（前端 mock 同序）
DUE_SORT_RANK: dict[str, int] = {
    "never": 0,
    "unmastered_1d": 1,
    "reviewing_3d": 2,
    "mastered_7d": 3,
}


@dataclass(frozen=True)
class DueRow:
    question: Question
    generated: GeneratedQuestion
    last_practiced_at: datetime | None
    due_reason: str


def _due_reason(
    mastery_status: str, last_practiced_at: datetime | None, now: datetime
) -> str | None:
    if last_practiced_at is None:
        return "never"
    days_needed = DUE_REVIEW_DAYS.get(mastery_status, 1)
    elapsed = (now - last_practiced_at).total_seconds()
    if elapsed < days_needed * 86_400:
        return None
    return DUE_REASON_BY_STATUS.get(mastery_status, "unmastered_1d")


def _pick_generated(
    generated: list[GeneratedQuestion], records: dict[int, list[PracticeRecord]]
) -> GeneratedQuestion:
    """每道原题只返 1 道：最近一次答错优先，其次练习次数少，最后 id。"""

    def key(row: GeneratedQuestion) -> tuple:
        items = records.get(row.id, [])
        last_wrong = max(
            (r.created_at for r in items if not r.is_correct), default=None
        )
        return (
            last_wrong is None,
            -(last_wrong.replace(tzinfo=UTC).timestamp() if last_wrong else 0),
            len(items),
            row.id,
        )

    return min(generated, key=key)


def list_due(
    session: Session,
    user_id: int,
    *,
    limit: int = DUE_LIMIT_DEFAULT,
    subject: str | None = None,
    now: datetime | None = None,
) -> tuple[list[DueRow], int]:
    """返回（截断后的到期条目, 截断前的总数）。

    - 只取未删除、属于当前用户的错题，且名下存在未删除生成题；
    - 到期：未练过优先；unmastered ≥1 天 / reviewing ≥3 天 / mastered ≥7 天；
    - 排序：未练过 → 最久未练 → 原题 id；limit 越界按 1–20 clamp。
    """
    limit = min(max(int(limit), 1), DUE_LIMIT_MAX)
    now = now or utcnow()

    stmt = select(Question).where(
        Question.user_id == user_id, Question.deleted_at.is_(None)
    )
    if subject:
        stmt = stmt.where(Question.subject == subject)
    questions = list(session.scalars(stmt.order_by(Question.id)))
    if not questions:
        return [], 0

    parent_ids = [q.id for q in questions]
    generated = list(
        session.scalars(
            select(GeneratedQuestion).where(
                GeneratedQuestion.parent_question_id.in_(parent_ids),
                GeneratedQuestion.user_id == user_id,
                GeneratedQuestion.deleted_at.is_(None),
            )
        )
    )
    if not generated:
        return [], 0

    generated_by_parent: dict[int, list[GeneratedQuestion]] = {}
    for row in generated:
        generated_by_parent.setdefault(row.parent_question_id, []).append(row)

    # 算「多久没练」要带上已软删的生成题：整组重生成会软删旧 3 题，但流水保留
    # （05「旧题的 practice_records 保留」）；只看未删的会把刚练过的题算成 never。
    record_rows = session.execute(
        select(PracticeRecord, GeneratedQuestion.parent_question_id)
        .join(GeneratedQuestion, GeneratedQuestion.id == PracticeRecord.generated_question_id)
        .where(
            GeneratedQuestion.user_id == user_id,
            GeneratedQuestion.parent_question_id.in_(parent_ids),
            PracticeRecord.user_id == user_id,
        )
    ).all()
    records_by_generated: dict[int, list[PracticeRecord]] = {}
    last_by_parent: dict[int, datetime] = {}
    for record, parent_id in record_rows:
        records_by_generated.setdefault(record.generated_question_id, []).append(record)
        if record.created_at > last_by_parent.get(parent_id, datetime.min):
            last_by_parent[parent_id] = record.created_at

    due: list[DueRow] = []
    for question in questions:
        candidates = generated_by_parent.get(question.id)
        if not candidates:
            continue
        # 返回哪道题只用未软删的 candidates；最近练习时间用含软删的全部流水
        last_practiced_at = last_by_parent.get(question.id)
        reason = _due_reason(question.mastery_status, last_practiced_at, now)
        if reason is None:
            continue
        due.append(
            DueRow(
                question=question,
                generated=_pick_generated(candidates, records_by_generated),
                last_practiced_at=last_practiced_at,
                due_reason=reason,
            )
        )

    total = len(due)
    # 口径 B（2026-11-28 定案）：未练过 → 掌握度越薄弱越前 → 同档内最久未练 → id
    due.sort(
        key=lambda row: (
            DUE_SORT_RANK.get(row.due_reason, len(DUE_SORT_RANK)),
            row.last_practiced_at or datetime.min,
            row.question.id,
        )
    )
    return due[:limit], total
