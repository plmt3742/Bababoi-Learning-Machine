"""后台任务 worker（12号 §3.2/§3.3）：消费 generation_task，调 LLM，写回结果。

设计要点：
- 独立线程 + 每步独立短事务；调 LLM 时不持有事务（05 §9.3）
- 启动时把 running 重置为 queued（进程重启不留卡死的任务）
- analysis：写回 question.analysis + 按 knowledge_points 同步 tags
- quiz：恰好 3 题校验通过后一次事务插入（全有或全无，05 §9.3）
- 失败自动重试 1 次，仍失败置 failed；任务中心可手动 retry
"""
from __future__ import annotations

import logging
import threading
import time
from functools import partial

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.ai import prompts, validator
from app.ai.client import OPERATION_ANALYSIS, OPERATION_QUIZ, build_llm_client
from app.ai.errors import AIError
from app.ai.pipeline import run as pipeline_run
from app.core.config import settings
from app.db.base import utcnow
from app.models import AiCallLog, GeneratedQuestion, GenerationTask, Question
from app.services.question_service import sync_tags, to_storage

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def _llm_client():
    global _client
    with _client_lock:
        if _client is None:
            _client = build_llm_client()
        return _client


def reset_stale_running(session_factory: sessionmaker) -> int:
    """启动时把上一进程留下的 running 任务放回队列。"""
    with session_factory() as session:
        stale = list(session.scalars(select(GenerationTask).where(GenerationTask.status == "running")))
        for task in stale:
            task.status = "queued"
        session.commit()
        return len(stale)


def _claim_next(session: Session) -> GenerationTask | None:
    """FIFO 领取一个任务。

    先查候选 id，再用条件 UPDATE（WHERE status='queued'）原子抢占：
    两个 worker 同时领到同一任务时，只有一个 rowcount=1，另一个下一圈再试。
    """
    candidate_id = session.scalar(
        select(GenerationTask.id)
        .where(GenerationTask.status == "queued")
        .order_by(GenerationTask.created_at.asc(), GenerationTask.id.asc())
        .limit(1)
    )
    if candidate_id is None:
        return None

    result = session.execute(
        update(GenerationTask)
        .where(GenerationTask.id == candidate_id, GenerationTask.status == "queued")
        .values(status="running", started_at=utcnow())
    )
    session.commit()
    if result.rowcount == 0:
        return None
    return session.get(GenerationTask, candidate_id)


def _question_payload(session: Session, question_id: int) -> dict:
    question = session.get(Question, question_id)
    return {
        "subject": question.subject,
        "chapter": question.chapter,
        "question_type": question.question_type,
        "content_md": question.content_md,
        "answer_md": question.answer_md,
        "explanation_md": question.explanation_md,
        "options": question.options,
        "blanks": question.blanks,
    }


def _write_call_log(
    session_factory: sessionmaker,
    task: GenerationTask,
    operation: str,
    status: str,
    usage=None,
    error_code: str | None = None,
    raw_text: str | None = None,
) -> None:
    """独立事务写 ai_call_logs（05 §9.3）：日志失败不影响主流程。"""
    try:
        with session_factory() as session:
            session.add(
                AiCallLog(
                    user_id=task.user_id,
                    question_id=task.question_id,
                    operation=operation,
                    model=usage.model if usage else settings.llm_model,
                    prompt_version=prompts.prompt_version(operation),
                    input_tokens=usage.prompt_tokens if usage else None,
                    output_tokens=usage.completion_tokens if usage else None,
                    latency_ms=usage.latency_ms if usage else 0,
                    queue_wait_ms=int(
                        (utcnow() - task.created_at).total_seconds() * 1000
                    ),
                    status=status,
                    error_code=error_code,
                    raw_response=(raw_text or "")[:8000],
                )
            )
            session.commit()
    except Exception:  # noqa: BLE001  # 日志写不进去不能拖垮任务
        logger.exception("ai_call_logs 写入失败（task=%s）", task.id)


def execute_task(session_factory: sessionmaker, task_id: int) -> None:
    """执行单个任务：调 pipeline，写结果。所有异常都转成任务失败，不往外抛。"""
    with session_factory() as session:
        task = session.get(GenerationTask, task_id)
        if task is None:
            return
        is_analysis = task.stage == "analysis"
        operation = OPERATION_ANALYSIS if is_analysis else OPERATION_QUIZ
        payload = _question_payload(session, task.question_id)
        messages = (
            prompts.analysis_messages(payload) if is_analysis
            else prompts.quiz_messages(payload)
        )
        user_id = task.user_id

    try:
        # retry_limit=0：任务级重试由 _fail_or_requeue 统一做（12号 §3.2 只重试 1 次），
        # pipeline 内部不再叠加重试，否则一个坏输出任务最多打 4 次 LLM
        result = pipeline_run(
            _llm_client(), operation, messages,
            parse=validator.AnalysisResult if is_analysis else None,
            # 原题题干要传进生成校验，否则拦不住「把原题抄一遍」这种坏输出（05 §7.2 第 3 条）
            custom_validate=(
                None
                if is_analysis
                else partial(
                    validator.validate_quiz,
                    original_content_md=payload["content_md"],
                    original_question_type=payload["question_type"],
                )
            ),
            retry_limit=0,
        )
        # 写回也在这一段里：落库异常一样得有终态，
        # 否则任务会永远停在 running，队列里白占一个并发位
        if is_analysis:
            _apply_analysis(session_factory, task_id, result)
        else:
            _apply_quiz(session_factory, task_id, result, user_id)
    except AIError as exc:
        # 坏输出的原文（pipeline 挂在 exc.raw_text 上）一定要落库：
        # 只记「AI_INVALID_OUTPUT」的话，没法定位是 prompt 的问题还是模型的问题
        _write_call_log(session_factory, task, operation, status="error",
                        error_code=exc.error_code, raw_text=exc.raw_text)
        _fail_or_requeue(session_factory, task_id, exc.error_code, exc.message)
        return
    except Exception as exc:  # noqa: BLE001  # 未预期异常也要让任务有终态
        logger.exception("任务 %s 执行异常", task_id)
        _write_call_log(session_factory, task, operation, status="error",
                        error_code="INTERNAL_ERROR", raw_text=str(exc))
        _fail_or_requeue(session_factory, task_id, "INTERNAL_ERROR", str(exc))
        return

    _write_call_log(session_factory, task, operation, status="success", usage=result.usage,
                    raw_text=result.usage.text)
    with session_factory() as session:
        t = session.get(GenerationTask, task_id)
        t.status = "done"
        t.finished_at = utcnow()
        session.commit()


def _apply_analysis(session_factory: sessionmaker, task_id: int, result) -> None:
    analysis = result.value
    with session_factory() as session:
        task = session.get(GenerationTask, task_id)
        question = session.get(Question, task.question_id)
        # answer_md/explanation_md 属于题目本体，不塞进 analysis JSON（确认单 14 号 §3）：
        # 两处都存就会各说各话，前端详情页读的是 question.answer_md。
        question.analysis = analysis.model_dump(exclude={"answer_md", "explanation_md"})
        # 原题已经填过的不覆盖——学生手写的答案优先于 AI 猜的
        if not (question.answer_md or "").strip():
            question.answer_md = analysis.answer_md
        if not (question.explanation_md or "").strip():
            question.explanation_md = analysis.explanation_md
        # merge=True：AI 知识点是追加，冲掉用户手动标签是数据丢失
        sync_tags(session, question, analysis.knowledge_points, merge=True)
        session.commit()


def _apply_quiz(session_factory: sessionmaker, task_id: int, result, user_id: int) -> None:
    specs = result.value
    with session_factory() as session:
        task = session.get(GenerationTask, task_id)
        # 详情页的「3 张题卡」是不变量：重新生成整组时先把旧组软删，
        # 否则再点一次生成就变 6 道。软删而不是物理删，
        # 已有的 practice_records 外键还要指回这些行。
        session.execute(
            update(GeneratedQuestion)
            .where(
                GeneratedQuestion.parent_question_id == task.question_id,
                GeneratedQuestion.deleted_at.is_(None),
            )
            .values(deleted_at=utcnow())
        )
        # 全有或全无：3 题一起插，任何一条插不进就整体回滚
        for spec in specs:
            session.add(
                GeneratedQuestion(
                    parent_question_id=task.question_id,
                    user_id=user_id,
                    content_md=spec.content_md,
                    answer_md=spec.answer_md,
                    explanation_md=spec.explanation_md,
                    question_type=spec.question_type,
                    options=to_storage(spec.options),
                    blanks=to_storage(spec.blanks),
                    difficulty=spec.difficulty,
                    model=result.usage.model,
                    prompt_version=prompts.prompt_version(OPERATION_QUIZ),
                    validation_status="valid",
                )
            )
        session.commit()


def _fail_or_requeue(session_factory: sessionmaker, task_id: int, code: str, message: str) -> None:
    with session_factory() as session:
        task = session.get(GenerationTask, task_id)
        if task is None:
            return
        if task.retry_index < settings.task_retry_limit:
            task.status = "queued"  # 自动重试：回队列排到队尾之后（按 created_at 排仍是老位置）
            task.retry_index += 1
        else:
            task.status = "failed"
            task.finished_at = utcnow()
        # 失败原因两种终态都记：requeue 时任务中心也要能看出「为什么又排了一次」
        task.error_code = code
        task.error_message = message
        session.commit()


def worker_loop(session_factory: sessionmaker, stop_event: threading.Event) -> None:
    """轮询队列直到 stop_event；空转间隔 1 秒。"""
    while not stop_event.is_set():
        try:
            with session_factory() as session:
                task = _claim_next(session)
            if task is None:
                stop_event.wait(1.0)
                continue
            logger.info("worker 领取任务 %s（stage=%s）", task.id, task.stage)
            execute_task(session_factory, task.id)
        except Exception:  # noqa: BLE001  # worker 单圈异常不能杀死线程
            logger.exception("worker 循环异常")
            stop_event.wait(1.0)


def start_workers(session_factory: sessionmaker, count: int) -> tuple[threading.Event, list[threading.Thread]]:
    stop_event = threading.Event()
    threads = [
        threading.Thread(
            target=worker_loop, args=(session_factory, stop_event),
            name=f"task-worker-{i}", daemon=True,
        )
        for i in range(max(1, count))
    ]
    for thread in threads:
        thread.start()
    return stop_event, threads


def stop_workers(stop_event: threading.Event, threads: list[threading.Thread], timeout_s: float = 10.0) -> None:
    stop_event.set()
    deadline = time.monotonic() + timeout_s
    for thread in threads:
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
