"""练习记录路由（05 §6.4）：两个端点，业务在 practice_service。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.models import User
from app.schemas.practice import (
    PracticeDueItem,
    PracticeDueOut,
    PracticeDueParent,
    PracticeRecordCreate,
    PracticeRecordOut,
    PracticeRecordPage,
)
from app.schemas.question import GeneratedQuestionOut, make_excerpt
from app.services import practice_service

router = APIRouter(prefix="/practice-records", tags=["practice"])

# 05 §6.5：今日待复习挂在 /practice 前缀下（与 /practice-records 分开）
due_router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("", response_model=PracticeRecordOut, status_code=201)
def create_practice_record(
    data: PracticeRecordCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PracticeRecordOut:
    return PracticeRecordOut.model_validate(practice_service.create(session, user.id, data))


@router.get("", response_model=PracticeRecordPage)
def list_practice_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.page_size_default, ge=1, le=settings.page_size_max),
    generated_question_id: int | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PracticeRecordPage:
    items, total = practice_service.list_records(
        session, user.id, page, page_size, generated_question_id
    )
    return PracticeRecordPage(
        items=[PracticeRecordOut.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@due_router.get("/due", response_model=PracticeDueOut)
def list_due_practice(
    limit: int = Query(default=6),
    subject: str | None = Query(default=None, max_length=32),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PracticeDueOut:
    """今日待复习队列；`limit` 越界按 1–20 clamp（前端固定传 6）。"""
    rows, total = practice_service.list_due(
        session, user.id, limit=limit, subject=subject or None
    )
    return PracticeDueOut(
        items=[
            PracticeDueItem(
                generated_question=GeneratedQuestionOut.model_validate(row.generated),
                parent=PracticeDueParent(
                    id=row.question.id,
                    subject=row.question.subject,
                    excerpt=make_excerpt(row.question.content_md),
                    mastery_status=row.question.mastery_status,
                ),
                last_practiced_at=row.last_practiced_at,
                due_reason=row.due_reason,
            )
            for row in rows
        ],
        total=total,
    )
