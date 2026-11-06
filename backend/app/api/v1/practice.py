"""练习记录路由（05 §6.4）：两个端点，业务在 practice_service。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.models import User
from app.schemas.practice import (
    PracticeRecordCreate,
    PracticeRecordOut,
    PracticeRecordPage,
)
from app.services import practice_service

router = APIRouter(prefix="/practice-records", tags=["practice"])


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
