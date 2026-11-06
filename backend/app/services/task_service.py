"""任务队列业务（12号 §3.2/§3.3 + ADR-006 三段并发）：入队、去重、重试、查询。

active-task 去重按 12号 §3.3 在 service 层做（DB 没有部分索引，见 models 的注释）。
一次生题排 3 段（每段 1 道题），去重键是 question_id + stage + target_index。
"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models import GeneratedQuestion, GenerationTask, Question

ACTIVE_STATUSES = ("queued", "running")

# ADR-006 / 14 号 Q1：P0 三段的难度档写死递增，自定义留 P1，但接口已经收 difficulties
SEGMENT_COUNT = 3
SEGMENT_DIFFICULTIES = ("easy", "medium", "hard")


def segment_difficulty(target_index: int, difficulty: str | None = None) -> str:
    """这一格该出什么难度：调用方给了就用给的，否则用默认递增档。"""
    if difficulty:
        return difficulty
    return SEGMENT_DIFFICULTIES[target_index - 1]


def _check_target_index(target_index: int | None) -> None:
    if target_index is not None and not 1 <= target_index <= SEGMENT_COUNT:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"target_index 必须在 1–{SEGMENT_COUNT} 之间，实际 {target_index}",
            400,
        )


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
    difficulty: str | None = None,
) -> GenerationTask:
    """入队一个任务；同 question+stage+target_index 已有 active 任务时直接复用它（防重复入队）。"""
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
        status="queued", target_index=target_index, difficulty=difficulty,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def enqueue_generation(
    session: Session,
    user_id: int,
    question_id: int,
    *,
    target_index: int | None = None,
    difficulties: list[str] | None = None,
    difficulty: str | None = None,
) -> list[GenerationTask]:
    """生题入队，返回本次涉及的段任务（14 号 D1）。

    - `target_index` 为空 = 整组：排 3 段，难度取 `difficulties`（省略则 easy/medium/hard 递增）
    - `target_index` 有值 = 单段（BE-015 的"重试这一段"）：只排那一段，难度取 `difficulty`
    """
    _check_target_index(target_index)

    if target_index is not None:
        slot = target_index
        return [enqueue(session, user_id, question_id, "quiz", slot,
                        segment_difficulty(slot, difficulty))]

    picked = difficulties or list(SEGMENT_DIFFICULTIES)
    if len(picked) != SEGMENT_COUNT:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"整组生成需要 {SEGMENT_COUNT} 个难度档，实际 {len(picked)} 个",
            400,
        )
    # 14 号 Q2-A：整组重生成入队即软删旧组，前端显示 3 张骨架卡，每段成功再写自己那格。
    # 只软删不物理删，已有的 practice_records 外键还要指回这些行。
    # 单段重生成不走这里——一段成功删整组会把另外两段的成果一起抹掉。
    session.execute(
        update(GeneratedQuestion)
        .where(
            GeneratedQuestion.parent_question_id == question_id,
            GeneratedQuestion.deleted_at.is_(None),
        )
        .values(deleted_at=utcnow())
    )
    session.commit()
    return [
        enqueue(session, user_id, question_id, "quiz", slot, segment_difficulty(slot, picked[slot - 1]))
        for slot in range(1, SEGMENT_COUNT + 1)
    ]


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
