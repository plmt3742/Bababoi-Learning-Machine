"""任务队列业务（12号 §3.2/§3.3）：入队、去重、重试、查询。

active-task 去重按 12号 §3.3 在 service 层做（DB 没有部分索引，见 models 的注释）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.models import GenerationTask, Question

ACTIVE_STATUSES = ("queued", "running")


def get_owned_question(session: Session, user_id: int, question_id: int) -> Question:
    """复用 BE-004 的归属校验；这里单独写一份避免 service 间互相 import 太深。"""
    question = session.get(Question, question_id)
    if question is None or question.deleted_at is not None:
        raise ApiError(ErrorCode.QUESTION_NOT_FOUND, "错题不存在或已删除", 404)
    if question.user_id != user_id:
        raise ApiError(ErrorCode.QUESTION_FORBIDDEN, "无权访问他人错题", 403)
    return question


def enqueue(
    session: Session,
    user_id: int,
    question_id: int,
    stage: str,
    target_index: int | None = None,
) -> GenerationTask:
    """入队一个任务；同 question+stage 已有 active 任务时直接复用它（防重复入队）。"""
    get_owned_question(session, user_id, question_id)

    existing = session.scalar(
        select(GenerationTask)
        .where(
            GenerationTask.question_id == question_id,
            GenerationTask.stage == stage,
            # 去重键含 target_index：单题重生成（BE-015）会针对某一题入队，
            # 不带它就会被同题的整组任务顶掉，反之也会顶掉别人
            GenerationTask.target_index.is_(None)
            if target_index is None
            else GenerationTask.target_index == target_index,
            GenerationTask.status.in_(ACTIVE_STATUSES),
        )
        .order_by(GenerationTask.created_at.desc())
    )
    if existing is not None:
        return existing

    task = GenerationTask(
        question_id=question_id, user_id=user_id, stage=stage,
        status="queued", target_index=target_index,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def list_tasks(
    session: Session,
    user_id: int,
    question_id: int | None = None,
    status: str | None = None,
) -> list[GenerationTask]:
    stmt = select(GenerationTask).where(GenerationTask.user_id == user_id)
    if question_id is not None:
        stmt = stmt.where(GenerationTask.question_id == question_id)
    if status:
        stmt = stmt.where(GenerationTask.status == status)
    return list(
        session.scalars(stmt.order_by(GenerationTask.created_at.desc(), GenerationTask.id.desc()))
    )


def get_owned_task(session: Session, user_id: int, task_id: int) -> GenerationTask:
    task = session.get(GenerationTask, task_id)
    if task is None:
        raise ApiError(ErrorCode.TASK_NOT_FOUND, "任务不存在", 404)
    if task.user_id != user_id:
        raise ApiError(ErrorCode.QUESTION_FORBIDDEN, "无权访问他人任务", 403)
    return task


def retry(session: Session, user_id: int, task_id: int) -> GenerationTask:
    """任务中心的重试按钮：failed 才能重试，manual 重试不受 retry_index 限制。"""
    task = get_owned_task(session, user_id, task_id)
    if task.status != "failed":
        raise ApiError(ErrorCode.VALIDATION_ERROR, "只有失败的任务可以重试", 400)
    task.status = "queued"
    task.error_code = None
    task.error_message = None
    task.retry_index += 1
    session.commit()
    session.refresh(task)
    return task
