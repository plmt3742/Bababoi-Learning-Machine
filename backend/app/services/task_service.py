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


def _enqueue_segment(
    session: Session,
    user_id: int,
    question_id: int,
    stage: str,
    target_index: int | None,
    difficulty: str | None,
) -> GenerationTask:
    """入队单段：同 question+stage+target_index 已有 active 任务时复用它，否则新建。

    不提交事务——整组入队要把软删旧组和 3 段入队放进同一次提交，边界交给调用方。
    """
    existing = session.scalar(
        select(GenerationTask)
        .where(
            GenerationTask.question_id == question_id,
            # 归属也进键：正常路径同题必同主；有脏数据时也不能复用/返回别人的任务
            GenerationTask.user_id == user_id,
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
    session.flush()
    return task


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
    task = _enqueue_segment(session, user_id, question_id, stage, target_index, difficulty)
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
    # 归属校验必须先于任何写操作：整组入口会软删旧组，
    # 放到 enqueue() 里做的话，越权请求会先删掉别人的生成题再拿到 403（issue #114）
    get_owned_question(session, user_id, question_id)

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
    # 例外：已有 active 段（重复点、部分在跑）时跳过软删——那些任务会被复用，
    # 已完成格若先删掉就会在新任务写好之前凭空消失；新任务成功时 worker 仍按格替换。
    has_active = session.scalar(
        select(GenerationTask.id)
        .where(
            GenerationTask.question_id == question_id,
            GenerationTask.user_id == user_id,
            GenerationTask.stage == "quiz",
            GenerationTask.status.in_(ACTIVE_STATUSES),
        )
        .limit(1)
    )
    if has_active is None:
        session.execute(
            update(GeneratedQuestion)
            .where(
                GeneratedQuestion.parent_question_id == question_id,
                # 归属上面已经校验过，这条是纵深防御：越权/脏数据都不该命中别人的行
                GeneratedQuestion.user_id == user_id,
                GeneratedQuestion.deleted_at.is_(None),
            )
            .values(deleted_at=utcnow())
        )
    # 软删与 3 段入队同一次提交：中途异常不会留下「旧组已删、任务没入队」
    tasks = [
        _enqueue_segment(session, user_id, question_id, "quiz", slot,
                         segment_difficulty(slot, picked[slot - 1]))
        for slot in range(1, SEGMENT_COUNT + 1)
    ]
    session.commit()
    for task in tasks:
        session.refresh(task)
    return tasks


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


# 取消被拒时的文案：前端直接把 message 显示给用户，一句「只有排队中的任务可以取消」
# 分不清是「已经在跑（等一下就好）」还是「已经结束（不用等了）」
CANCEL_BLOCKED_MESSAGES = {
    "running": "任务已开始执行，无法取消",
    "done": "任务已完成，无法取消",
    "failed": "任务已失败，无法取消",
    "canceled": "任务已取消，无需重复操作",
}


def cancel(session: Session, user_id: int, task_id: int) -> GenerationTask:
    """取消排队中的任务（BE-027）。

    只认 `queued`：`running` 是在途同步请求，打断不了（取消了模型也照样扣费），
    所以直接拒绝。条件 UPDATE 和 worker 的 `_claim_next` 抢同一行时只能有一个成功，
    另一个拿到 rowcount=0，不会出现「取消了但任务还在跑」。
    """
    task = get_owned_task(session, user_id, task_id)
    result = session.execute(
        update(GenerationTask)
        .where(GenerationTask.id == task.id, GenerationTask.status == "queued")
        # error_* 一起清：自动重排后的任务还带着上一轮失败原因，
        # 取消后前端/接口不该再显示一条和「已取消」矛盾的错误（retry 同样会清）
        .values(
            status="canceled",
            finished_at=utcnow(),
            error_code=None,
            error_message=None,
        )
    )
    session.commit()
    if result.rowcount == 0:
        # 条件没命中说明状态已经被 worker/别的请求改掉：回读真实状态再报错，
        # 文案才能区分「在跑」与「已结束」；这一步同时把内存对象对齐到库里的值
        session.refresh(task)
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            CANCEL_BLOCKED_MESSAGES.get(task.status, "任务当前状态不可取消"),
            400,
        )
    session.refresh(task)
    return task
