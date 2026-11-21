"""识图任务服务（B 档，05 §6.8）：提交 / 查询 / 领取 / 收尾 / 自愈。

名额三层（别混成一个数）：
- 同时运行：`vision_max_concurrency` 个 worker；
- 全局排队：`vision_queue_max_depth` 上限，且预估等待 > `vision_queue_wait_max_s`
  时**在提交时就拒绝**（429 + Retry-After），不做"先收单、排到再判死"；
- 每人：`active_slot` 唯一约束，同时只允许 1 个未完成任务；参数全等则复用。
"""
from __future__ import annotations

import json
import math
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models.vision import (
    VISION_JOB_ACTIVE_STATUSES,
    VISION_JOB_TERMINAL_STATUSES,
    VisionJob,
)
from app.services import extraction_service

JOB_TTL = timedelta(hours=24)
DEFAULT_AVG_SECONDS = 25.0
# 准入闸要保守：均值会被最近几张快图拉低，低估的代价是"排了队再被判死"。
# 20 是 8 并发真图 soak 的单张实测（19.3s）取整；宁可多拒几个人 30 秒后重试。
MIN_AVG_SECONDS = 20.0
RETRY_AFTER_HEADERS = {"Retry-After": "30"}


def _queued_count(session: Session) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(VisionJob).where(VisionJob.status == "queued")
        )
        or 0
    )


def _ahead_count(session: Session) -> int:
    """新任务前面还有多少个：排队 + **正在跑的**。

    少了 running 那 8 个，估算会少一整批——准入放行后实际等着更久，
    到认领时又被排队上限判死（"干等 75 秒然后失败"）。
    """
    return (
        session.scalar(
            select(func.count())
            .select_from(VisionJob)
            .where(VisionJob.status.in_(VISION_JOB_ACTIVE_STATUSES))
        )
        or 0
    )


def _avg_runtime_seconds(session: Session) -> float:
    rows = session.scalars(
        select(VisionJob)
        .where(
            VisionJob.status == "done",
            VisionJob.started_at.is_not(None),
            VisionJob.finished_at.is_not(None),
        )
        .order_by(VisionJob.finished_at.desc())
        .limit(20)
    ).all()
    durations = [
        (row.finished_at - row.started_at).total_seconds()
        for row in rows
        if row.started_at is not None and row.finished_at is not None
    ]
    if not durations:
        return DEFAULT_AVG_SECONDS
    return max(sum(durations) / len(durations), MIN_AVG_SECONDS)


def _estimate_wait_s(session: Session, ahead: int) -> int:
    workers = max(1, settings.vision_max_concurrency)
    return max(1, math.ceil(ahead / workers * _avg_runtime_seconds(session)))


def _same_params(job: VisionJob, image_path: str, subject: str | None, force_refresh: bool) -> bool:
    return (
        job.image_path == image_path
        and (job.subject or "") == (subject or "")
        and job.force_refresh == force_refresh
    )


def _active_job(session: Session, user_id: int) -> VisionJob | None:
    return session.scalar(
        select(VisionJob).where(
            VisionJob.user_id == user_id,
            VisionJob.status.in_(VISION_JOB_ACTIVE_STATUSES),
        )
    )


def _submit_out(
    job: VisionJob,
    *,
    reused: bool,
    queue_position: int | None = None,
    estimated_wait_s: int | None = None,
) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "reused": reused,
        "queue_position": queue_position,
        "estimated_wait_s": estimated_wait_s,
        "result": None,
    }


def submit(
    session: Session,
    session_factory: sessionmaker,
    user_id: int,
    *,
    image_path: str,
    subject: str | None,
    force_refresh: bool,
) -> dict:
    """提交识图任务。

    - 命中缓存（且非强刷）→ 直接返回结果，不建行、不进队列；
    - 强刷冷却 → 提交时 429（不排队）；
    - 已有 active 任务 → 参数全等复用单号，不同参数 429；
    - 队列深度/预估等待超限 → 429 + Retry-After（准入闸，不先收单再判死）。
    """
    subject = subject.strip() if subject and subject.strip() else None
    key, cached = extraction_service.prepare_submission(
        session_factory,
        user_id,
        image_path,
        subject=subject,
        force_refresh=force_refresh,
    )
    if cached is not None:
        return {
            "job_id": None,
            "status": "done",
            "reused": False,
            "queue_position": None,
            "estimated_wait_s": None,
            "result": cached,
        }

    active = _active_job(session, user_id)
    if active is not None:
        if _same_params(active, image_path, subject, force_refresh):
            return _submit_out(active, reused=True)
        raise ApiError(
            ErrorCode.VISION_PREVIOUS_PENDING,
            "上一张还在识别，请稍等",
            429,
        )

    # 准入按"前面还有多少"估（排队 + running），队列入队上限只看 queued
    depth = _queued_count(session)
    ahead = _ahead_count(session)
    wait_s = _estimate_wait_s(session, ahead)
    if depth >= settings.vision_queue_max_depth or wait_s > settings.vision_queue_wait_max_s:
        raise ApiError(
            ErrorCode.VISION_QUEUE_FULL,
            "当前识图排队较多，请稍后再试",
            429,
            headers=RETRY_AFTER_HEADERS,
        )

    # 到这里才真正扣强刷额度：被上面 any 一步拒掉的人不该丢一次冷却
    if force_refresh:
        extraction_service.take_force_slot(session_factory, key)

    now = utcnow()
    job = VisionJob(
        user_id=user_id,
        image_path=image_path,
        subject=subject,
        force_refresh=force_refresh,
        status="queued",
        active_slot=user_id,
        created_at=now,
        expires_at=now + JOB_TTL,
    )
    session.add(job)
    try:
        session.commit()
    except IntegrityError:
        # 并发提交（多标签页）：active_slot 唯一约束兜底，重查一次按参数决定复用还是 429
        session.rollback()
        active = _active_job(session, user_id)
        if active is not None and _same_params(active, image_path, subject, force_refresh):
            return _submit_out(active, reused=True)
        raise ApiError(
            ErrorCode.VISION_PREVIOUS_PENDING,
            "上一张还在识别，请稍等",
            429,
        ) from None
    session.refresh(job)
    return _submit_out(
        job, reused=False, queue_position=ahead + 1, estimated_wait_s=wait_s
    )


def get_for_user(session: Session, user_id: int, job_id: int) -> dict:
    job = session.get(VisionJob, job_id)
    # 越权按"不存在"处理：不承认别人的任务存在（沿用取图 404 的语义）
    if job is None or job.user_id != user_id:
        raise ApiError(ErrorCode.VISION_JOB_NOT_FOUND, "识图任务不存在", 404)
    result = json.loads(job.result_json) if job.result_json else None
    error = None
    if job.error_code:
        error = {"code": job.error_code, "message": job.error_message or "识图失败"}
    queue_position = None
    estimated_wait_s = None
    if job.status == "queued":
        # 刷新页面后还能显示"前面还有几个"：只数排在它前面的活动任务（id 单调）
        ahead = session.scalar(
            select(func.count())
            .select_from(VisionJob)
            .where(VisionJob.status.in_(VISION_JOB_ACTIVE_STATUSES), VisionJob.id < job.id)
        ) or 0
        queue_position = ahead + 1
        estimated_wait_s = _estimate_wait_s(session, ahead)
    return {
        "job_id": job.id,
        "status": job.status,
        "queue_position": queue_position,
        "estimated_wait_s": estimated_wait_s,
        "result": result,
        "error": error,
    }


def claim_next(session: Session) -> VisionJob | None:
    """FIFO 领取一个任务；两段式 CAS，SQLite/MySQL 通用。

    首次认领（attempts=0）先判排队时长：超过 `vision_queue_wait_max_s` 直接置 failed，
    不再调模型。重排过的任务（attempts>=1）跳过这个判断——`created_at` 是原始提交时间，
    不能拿它把"崩溃重排"误判成"排队太久"。
    """
    candidate_id = session.scalar(
        select(VisionJob.id)
        .where(VisionJob.status == "queued")
        .order_by(VisionJob.created_at.asc(), VisionJob.id.asc())
        .limit(1)
    )
    if candidate_id is None:
        return None

    now = utcnow()
    candidate = session.get(VisionJob, candidate_id)
    if candidate is None:
        return None
    if (
        candidate.attempts == 0
        and (now - candidate.created_at).total_seconds() > settings.vision_queue_wait_max_s
    ):
        candidate.status = "failed"
        candidate.error_code = str(ErrorCode.VISION_QUEUE_TIMEOUT)
        candidate.error_message = "排队时间过长，请稍后重试"
        candidate.finished_at = now
        candidate.active_slot = None
        session.commit()
        return None

    result = session.execute(
        update(VisionJob)
        .where(VisionJob.id == candidate_id, VisionJob.status == "queued")
        .values(
            status="running",
            started_at=now,
            deadline_at=now + timedelta(seconds=settings.vision_run_deadline_s),
            attempts=VisionJob.attempts + 1,
        )
    )
    session.commit()
    if result.rowcount == 0:
        return None  # 被别人抢走，下一圈再试
    return session.get(VisionJob, candidate_id)


def mark_done(session: Session, job_id: int, payload: dict) -> None:
    session.execute(
        update(VisionJob)
        .where(VisionJob.id == job_id, VisionJob.status == "running")
        .values(
            status="done",
            result_json=json.dumps(payload, ensure_ascii=False),
            finished_at=utcnow(),
            active_slot=None,
        )
    )
    session.commit()


def mark_failed(session: Session, job_id: int, code: str, message: str) -> None:
    session.execute(
        update(VisionJob)
        .where(VisionJob.id == job_id, VisionJob.status == "running")
        .values(
            status="failed",
            error_code=code,
            error_message=message,
            finished_at=utcnow(),
            active_slot=None,
        )
    )
    session.commit()


def recover_stale(session_factory: sessionmaker) -> int:
    """启动自愈：卡住的 running 放回队列；连续中断两次的直接 failed。"""
    cutoff = utcnow() - timedelta(seconds=settings.vision_run_deadline_s + 60)
    with session_factory() as session:
        stale = session.scalars(
            select(VisionJob).where(
                VisionJob.status == "running", VisionJob.started_at < cutoff
            )
        ).all()
        for job in stale:
            if job.attempts >= 2:
                job.status = "failed"
                job.error_code = str(ErrorCode.AI_TIMEOUT)
                job.error_message = "识图任务中断，请重试"
                job.finished_at = utcnow()
                job.active_slot = None
            else:
                job.status = "queued"
                job.started_at = None
                job.deadline_at = None
        session.commit()
        return len(stale)


def cleanup_expired(session_factory: sessionmaker) -> int:
    """删掉过期的终态任务；绝不能误删 queued/running。"""
    with session_factory() as session:
        result = session.execute(
            delete(VisionJob).where(
                VisionJob.expires_at < utcnow(),
                VisionJob.status.in_(VISION_JOB_TERMINAL_STATUSES),
            )
        )
        session.commit()
        return result.rowcount or 0
