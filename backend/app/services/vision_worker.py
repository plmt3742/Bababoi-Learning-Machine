"""识图任务 worker（B 档，05 §6.8）：独立线程组消费 vision_job。

与生题 worker 分开：一张图最长 2 分钟，混进 6 个生题线程会把"生成变式题"一起饿死。
超时是协作式的：worker 不杀线程，而是把整单 deadline 传进 pipeline，每次调用前
按剩余时间收紧 timeout；剩余不足 5 秒就不再发起调用。
"""
from __future__ import annotations

import logging
import threading
import time

from sqlalchemy.orm import sessionmaker

from app.ai.errors import AIError
from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models.vision import VisionJob
from app.schemas.image import ImageExtractionOut
from app.services import extraction_service, vision_job_service

logger = logging.getLogger(__name__)

CLAIM_IDLE_WAIT_S = 0.5
CLEANUP_INTERVAL_S = 300
SWEEP_INTERVAL_S = 30


def execute_job(session_factory: sessionmaker, job_id: int) -> None:
    """跑一个已认领的任务；同步函数，测试直接调它。"""
    with session_factory() as session:
        job = session.get(VisionJob, job_id)
        if job is None or job.status != "running" or job.deadline_at is None:
            return
        user_id = job.user_id
        image_path = job.image_path
        subject = job.subject
        force_refresh = job.force_refresh
        remaining = (job.deadline_at - utcnow()).total_seconds()

    deadline = time.monotonic() + max(0.0, remaining)
    try:
        payload = extraction_service.extract_from_image(
            session_factory,
            user_id,
            image_path,
            subject=subject,
            force_refresh=force_refresh,
            deadline=deadline,
            call_timeout_s=settings.vision_call_timeout_s,
            # 提交时已占过强刷冷却额度，worker 里不能再占一次（否则会被自己挡住）
            force_slot_taken=force_refresh,
        )
        result = ImageExtractionOut.model_validate(payload).model_dump(mode="json")
    except ApiError as exc:
        with session_factory() as session:
            vision_job_service.mark_failed(session, job_id, str(exc.code), exc.message)
        return
    except AIError as exc:
        with session_factory() as session:
            vision_job_service.mark_failed(session, job_id, exc.error_code, exc.message)
        return
    except Exception:  # noqa: BLE001 未预期异常也要落终态，不能让任务永远 running
        logger.exception("识图任务执行失败（job=%s）", job_id)
        with session_factory() as session:
            vision_job_service.mark_failed(
                session, job_id, str(ErrorCode.INTERNAL_ERROR), "识图任务内部错误"
            )
        return

    with session_factory() as session:
        vision_job_service.mark_done(session, job_id, result)


def worker_loop(session_factory: sessionmaker, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            with session_factory() as session:
                job = vision_job_service.claim_next(session)
            if job is None:
                stop_event.wait(CLAIM_IDLE_WAIT_S)
                continue
            execute_job(session_factory, job.id)
        except Exception:  # noqa: BLE001 worker 不能因为一次异常整组退出
            logger.exception("识图 worker 循环异常")
            stop_event.wait(CLAIM_IDLE_WAIT_S)


def janitor_loop(session_factory: sessionmaker, stop_event: threading.Event) -> None:
    """运行期自愈 + 终态清理：独立线程，不消费任务。

    不能塞进 worker_loop：execute_job 是同步阻塞的，最长占满一整单 140s，
    队列持续有任务时"每 30s 扫一次"会退化成"每个任务扫一次"——
    而卡住的单恰恰在最忙的时候才最需要自愈。
    """
    last_cleanup = time.monotonic()
    while not stop_event.is_set():
        # stop 时 wait 立刻返回，join 不用等满一轮
        if stop_event.wait(SWEEP_INTERVAL_S):
            return
        try:
            recovered = vision_job_service.recover_stale_running(session_factory)
            if recovered:
                logger.warning("运行期自愈：重置/终止了 %d 个卡住的识图任务", recovered)
        except Exception:  # noqa: BLE001 一轮失败不能让线程死掉，下一轮再来
            logger.exception("识图任务运行期自愈失败")
        now = time.monotonic()
        if now - last_cleanup > CLEANUP_INTERVAL_S:
            last_cleanup = now
            try:
                removed = vision_job_service.cleanup_expired(session_factory)
                if removed:
                    logger.info("清理过期识图任务 %d 条", removed)
            except Exception:  # noqa: BLE001 清理失败不影响自愈
                logger.exception("清理过期识图任务失败")


def start_workers(
    session_factory: sessionmaker, count: int
) -> tuple[threading.Event, list[threading.Thread]]:
    """启动独立线程组；返回 (stop_event, threads)，由 lifespan 负责停。"""
    stop_event = threading.Event()
    threads = [
        threading.Thread(
            target=worker_loop,
            args=(session_factory, stop_event),
            name=f"vision-worker-{index + 1}",
            daemon=True,
        )
        for index in range(max(1, count))
    ]
    threads.append(
        threading.Thread(
            target=janitor_loop,
            args=(session_factory, stop_event),
            name="vision-janitor",
            daemon=True,
        )
    )
    for thread in threads:
        thread.start()
    return stop_event, threads


def stop_workers(stop_event: threading.Event, threads: list[threading.Thread]) -> None:
    stop_event.set()
    for thread in threads:
        thread.join(timeout=5)
