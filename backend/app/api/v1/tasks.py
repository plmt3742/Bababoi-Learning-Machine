"""任务与分析/生成入队路由（05 §6.4/§6.5b）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.question import TaskOut
from app.services import task_service

router = APIRouter(tags=["tasks"])


def _task_id_response(task) -> dict:
    return {"task_id": task.id}


@router.post("/questions/{question_id}/analyze")
def analyze_question(
    question_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """重新分析：入队 analysis 任务；已有进行中的同 stage 任务时复用。"""
    task = task_service.enqueue(session, user.id, question_id, stage="analysis")
    return _task_id_response(task)


@router.post("/questions/{question_id}/generate")
def generate_question(
    question_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """生成 3 道同类题：入队 quiz 任务；worker 完成后写 generated_questions。"""
    task = task_service.enqueue(session, user.id, question_id, stage="quiz")
    return _task_id_response(task)


@router.get("/tasks")
def list_tasks(
    question_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """任务中心/轮询兜底（05 §6.5b）。"""
    tasks = task_service.list_tasks(session, user.id, question_id, status)
    return {"items": [TaskOut.model_validate(t) for t in tasks]}


@router.post("/tasks/{task_id}/retry", response_model=TaskOut)
def retry_task(
    task_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TaskOut:
    return TaskOut.model_validate(task_service.retry(session, user.id, task_id))
