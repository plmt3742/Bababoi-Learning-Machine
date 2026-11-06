"""错题路由（05 §6.4）：五个端点都是薄壳，业务在 question_service。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.models import User
from app.schemas.question import (
    GeneratedQuestionOut,
    MasterStatus,
    QuestionCreate,
    QuestionCreateOut,
    QuestionDetail,
    QuestionOut,
    QuestionPage,
    QuestionUpdate,
    TaskOut,
)
from app.services import question_service

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", response_model=QuestionCreateOut)
def create_question(
    data: QuestionCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> QuestionCreateOut:
    question, task = question_service.create(session, user.id, data)
    return QuestionCreateOut(question=QuestionOut.model_validate(question), task_id=task.id)


@router.get("", response_model=QuestionPage)
def list_questions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.page_size_default, ge=1, le=settings.page_size_max),
    subject: str | None = None,
    tag: str | None = None,
    mastery_status: MasterStatus | None = None,
    q: str | None = Query(default=None, max_length=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> QuestionPage:
    items, total = question_service.list_questions(
        session,
        user.id,
        page=page,
        page_size=page_size,
        subject=subject,
        tag=tag,
        mastery_status=mastery_status,
        q=q,
    )
    return QuestionPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{question_id}", response_model=QuestionDetail)
def get_question(
    question_id: int,
    include: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> QuestionDetail:
    question = question_service.get_detail(session, user.id, question_id)
    detail = QuestionDetail.model_validate(question)
    detail.tasks = [
        TaskOut.model_validate(t) for t in question_service.list_tasks(session, question.id)
    ]
    if include and "generated" in include.split(","):
        detail.generated_questions = [
            GeneratedQuestionOut.model_validate(g)
            for g in question_service.list_generated(session, user.id, question.id)
        ]
    return detail


@router.patch("/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: int,
    data: QuestionUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> QuestionOut:
    question = question_service.update(session, user.id, question_id, data)
    return QuestionOut.model_validate(question)


@router.delete("/{question_id}", status_code=204)
def delete_question(
    question_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    question_service.soft_delete(session, user.id, question_id)
