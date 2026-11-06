"""后台任务 worker（12号 §3.2/§3.3 + ADR-006 三段并发）：消费 generation_task，调 LLM，写回结果。

设计要点：
- 独立线程 + 每步独立短事务；调 LLM 时不持有事务（05 §9.3）
- 启动时把 running 重置为 queued（进程重启不留卡死的任务）
- analysis：写回 question.analysis + 按 knowledge_points 同步 tags
- quiz：一段一题，成功后只写自己那一格（target_index），不动其它两段
- 失败自动重试 1 次（requeue，且跑完不到 90s 才排），仍失败置 failed；任务中心可手动 retry
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
from app.models import GeneratedQuestion, GenerationTask, Question, User
from app.services import ai_log
from app.services.question_service import sync_tags, to_storage
from app.services.task_service import segment_difficulty

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def _llm_client():
    """worker 用的客户端；测试 monkeypatch 这个函数换替身。"""
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
    analysis = question.analysis or {}
    return {
        "subject": question.subject,
        "chapter": question.chapter,
        "question_type": question.question_type,
        "content_md": question.content_md,
        "answer_md": question.answer_md,
        "explanation_md": question.explanation_md,
        "options": question.options,
        "blanks": question.blanks,
        # 生成段的提示词要"同知识点"（14 号 D2）：优先用分析结果，
        # 分析还没跑就用用户打的标签，两个都没有时提示词里会写"自己从题干判断"
        "knowledge_points": analysis.get("knowledge_points") or [],
        "tags": [tag.name for tag in question.tags],
    }


def _write_call_log(
    session_factory: sessionmaker,
    task: GenerationTask,
    operation: str,
    status: str,
    usage=None,
    error_code: str | None = None,
    raw_text: str | None = None,
    type_policy: str | None = None,
) -> None:
    """任务侧的薄封装：归属和排队时长从 task 上取，写库规则交给 ai_log（05 §9.3）。"""
    ai_log.write_call_log(
        session_factory,
        task.user_id,
        operation,
        status,
        question_id=task.question_id,
        usage=usage,
        error_code=error_code,
        raw_text=raw_text,
        queue_wait_ms=int((utcnow() - task.created_at).total_seconds() * 1000),
        type_policy=type_policy,
    )


def execute_task(session_factory: sessionmaker, task_id: int) -> None:
    """执行单个任务：调 pipeline，写结果。所有异常都转成任务失败，不往外抛。"""
    with session_factory() as session:
        task = session.get(GenerationTask, task_id)
        if task is None:
            return
        is_analysis = task.stage == "analysis"
        operation = OPERATION_ANALYSIS if is_analysis else OPERATION_QUIZ
        payload = _question_payload(session, task.question_id)
        user_id = task.user_id
        question_id = task.question_id
        # 迁移前入队的 quiz 任务没有这两列，按默认递增档跑（slot 落 1），
        # 不然老库里一条 queued 的旧任务会在这里 KeyError 变 INTERNAL_ERROR
        slot = task.target_index or 1
        difficulty = task.difficulty or segment_difficulty(slot)
        # BE-026（issue #44）：题型一致性开关在**执行时**读，不在入队时快照。
        # 用户在任务排队期间改了设置，跑出来的就该按新设置——入队快照会出现
        # "我明明关了开关还是被拒"这种没法解释的状态差。
        # 读不到用户（理论上只剩历史脏数据）按默认开启处理，与列的 DEFAULT 一致。
        owner = session.get(User, user_id)
        enforce = bool(owner.enforce_same_question_type) if owner else True
        type_policy = None if is_analysis else ("strict" if enforce else "soft")
        if is_analysis:
            messages = prompts.analysis_messages(payload)
        else:
            messages = prompts.quiz_messages(payload, target_index=slot, difficulty=difficulty)
            siblings = tuple(
                row.content_md
                for row in session.scalars(
                    select(GeneratedQuestion).where(
                        GeneratedQuestion.parent_question_id == question_id,
                        GeneratedQuestion.deleted_at.is_(None),
                    )
                )
                # 同组其它格：用 Python 比而不是 SQL 的 !=，因为 target_index
                # 可能是 NULL（迁移前的老行），NULL != 1 在 SQL 里不成立，
                # 那些老题就会既不被排除、也不参与查重
                if row.target_index != slot
            )

    try:
        # retry_limit=0：任务级重试由 _fail_or_requeue 统一做（12号 §3.2 只重试 1 次），
        # pipeline 内部不再叠加重试，否则一个坏输出任务最多打 4 次 LLM
        result = pipeline_run(
            _llm_client(), operation, messages,
            parse=validator.AnalysisResult if is_analysis else None,
            # 原题题干与同组其它段都要传进校验：前者拦「把原题抄一遍」，
            # 后者拦「两段出了逐字相同的题」（05 §7.2 第 3 条）
            custom_validate=(
                None
                if is_analysis
                else partial(
                    validator.validate_segment,
                    difficulty=difficulty,
                    original_content_md=payload["content_md"],
                    sibling_content_mds=siblings,
                    original_question_type=payload["question_type"],
                    type_policy=type_policy or "soft",
                )
            ),
            retry_limit=0,
        )
        # 写回也在这一段里：落库异常一样得有终态，
        # 否则任务会永远停在 running，队列里白占一个并发位
        if is_analysis:
            _apply_analysis(session_factory, task_id, result)
        else:
            _apply_segment(session_factory, task_id, result, user_id, slot, difficulty)
    except AIError as exc:
        # 坏输出的原文（pipeline 挂在 exc.raw_text 上）一定要落库：
        # 只记「AI_INVALID_OUTPUT」的话，没法定位是 prompt 的问题还是模型的问题
        _write_call_log(session_factory, task, operation, status="error",
                        error_code=exc.error_code, raw_text=exc.raw_text,
                        type_policy=type_policy)
        _fail_or_requeue(session_factory, task_id, exc.error_code, exc.message)
        return
    except Exception as exc:  # noqa: BLE001  # 未预期异常也要让任务有终态
        logger.exception("任务 %s 执行异常", task_id)
        _write_call_log(session_factory, task, operation, status="error",
                        error_code="INTERNAL_ERROR", raw_text=str(exc),
                        type_policy=type_policy)
        _fail_or_requeue(session_factory, task_id, "INTERNAL_ERROR", str(exc))
        return

    _write_call_log(session_factory, task, operation, status="success", usage=result.usage,
                    raw_text=result.usage.text, type_policy=type_policy)
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


def _apply_segment(
    session_factory: sessionmaker, task_id: int, result, user_id: int,
    slot: int, difficulty: str,
) -> None:
    """一段成功只写自己那一格（14 号 Q2-A 的按格替换）。

    软删范围限定在同一个 target_index：一段成功就删整组会把另外两段刚写好的题抹掉，
    那是并发 worker 之间最容易互相踩的地方，所以宁可留同一格的历史行也不跨格删。
    """
    spec = result.value
    with session_factory() as session:
        task = session.get(GenerationTask, task_id)
        session.execute(
            update(GeneratedQuestion)
            .where(
                GeneratedQuestion.parent_question_id == task.question_id,
                GeneratedQuestion.deleted_at.is_(None),
                GeneratedQuestion.target_index == slot,
            )
            .values(deleted_at=utcnow())
        )
        session.add(
            GeneratedQuestion(
                parent_question_id=task.question_id,
                user_id=user_id,
                target_index=slot,
                content_md=spec.content_md,
                answer_md=spec.answer_md,
                explanation_md=spec.explanation_md,
                question_type=spec.question_type,
                options=to_storage(spec.options),
                blanks=to_storage(spec.blanks),
                difficulty=difficulty,
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
        # 14 号 D8：跑过 90s 的段不再自动重排。三段并发下一个坏输出如果排队重试，
        # 用户会在骨架卡上等到 4 分钟；直接 failed 让前端出"这一格可重试"的卡更快有终态。
        ran_s = (utcnow() - task.started_at).total_seconds() if task.started_at else 0.0
        if task.retry_index < settings.task_retry_limit and ran_s <= settings.task_requeue_deadline_s:
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
