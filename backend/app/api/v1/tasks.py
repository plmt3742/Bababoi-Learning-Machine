"""任务与分析/生成入队路由（05 §6.4/§6.5b）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.question import GenerateRequest, TaskOut
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
    body: GenerateRequest | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """生题入队（ADR-006）：整组排 3 段、单段重排 1 段，返回本次涉及的段。

    请求体可整个省略（详情页那个"生成 3 道同类题"按钮就是这么点的），
    省略 = 整组 + 默认递增难度。
    """
    params = body or GenerateRequest()
    tasks = task_service.enqueue_generation(
        session, user.id, question_id,
        target_index=params.target_index,
        difficulties=params.difficulties,
        difficulty=params.difficulty,
    )
    # 14 号 D1 / Q3：不再返回单个 task_id，一次切净（前端 FE-023 #28 已按 tasks[] 兼容过）
    return {
        "tasks": [
            {"task_id": task.id, "target_index": task.target_index, "difficulty": task.difficulty}
            for task in tasks
        ]
    }


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
