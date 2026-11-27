"""管理端列表 DTO 组装（ADM-003/007）。

集中在一处的原因：列表页、详情页、概览里的同一实体必须给出同一形状；写操作返回
的也是这些 DTO，不能各写一份。这里只读 DB，不改数据。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import (
    AdminAuditLog,
    AiCallLog,
    GeneratedQuestion,
    GenerationTask,
    PasswordResetRequest,
    PracticeRecord,
    Question,
    User,
    UserAiSettings,
)
from app.schemas.admin import (
    AdminTask,
    AdminTaskDetail,
    AdminUser,
    AdminUserDetail,
    AiLog,
    AuditLog,
    PasswordRequest,
    TaskTimelineItem,
)
from app.utils.admin_time import fmt_latency, fmt_task_duration, fmt_tokens, to_display

_EXCERPT_MAX = 80


def _excerpt(text: str | None) -> str:
    if not text:
        return ""
    flat = " ".join(text.split())
    return flat if len(flat) <= _EXCERPT_MAX else flat[:_EXCERPT_MAX] + "…"


def _user_counts(session: Session, user_ids: list[int]) -> dict[int, tuple[int, int, int]]:
    """(questions, generated, practice) 按用户批量统计，避免列表 N+1。"""
    if not user_ids:
        return {}
    questions = dict(
        session.execute(
            select(Question.user_id, func.count())
            .where(Question.user_id.in_(user_ids), Question.deleted_at.is_(None))
            .group_by(Question.user_id)
        ).all()
    )
    generated = dict(
        session.execute(
            select(GeneratedQuestion.user_id, func.count())
            .where(
                GeneratedQuestion.user_id.in_(user_ids),
                GeneratedQuestion.deleted_at.is_(None),
            )
            .group_by(GeneratedQuestion.user_id)
        ).all()
    )
    practice = dict(
        session.execute(
            select(PracticeRecord.user_id, func.count())
            .where(PracticeRecord.user_id.in_(user_ids))
            .group_by(PracticeRecord.user_id)
        ).all()
    )
    return {
        uid: (questions.get(uid, 0), generated.get(uid, 0), practice.get(uid, 0))
        for uid in user_ids
    }


def _pending_requests(session: Session, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = session.execute(
        select(PasswordResetRequest.user_id, func.count())
        .where(
            PasswordResetRequest.user_id.in_(user_ids),
            PasswordResetRequest.status == "pending",
        )
        .group_by(PasswordResetRequest.user_id)
    ).all()
    return dict(rows)


def _byok(session: Session, user_ids: list[int]) -> dict[int, UserAiSettings]:
    if not user_ids:
        return {}
    return {
        row.user_id: row
        for row in session.scalars(
            select(UserAiSettings).where(UserAiSettings.user_id.in_(user_ids))
        )
    }


def build_users(session: Session, users: list[User]) -> list[AdminUser]:
    ids = [u.id for u in users]
    counts = _user_counts(session, ids)
    pending = _pending_requests(session, ids)
    byok = _byok(session, ids)
    result = []
    for user in users:
        q_count, g_count, p_count = counts.get(user.id, (0, 0, 0))
        key = byok.get(user.id)
        result.append(
            AdminUser(
                id=user.id,
                username=user.username,
                email=user.email or "",
                status="disabled" if user.disabled_at is not None else "active",
                role=user.role,
                questions=q_count,
                generated=g_count,
                practice=p_count,
                last_login=to_display(user.last_login_at, seconds=False),
                created_at=to_display(user.created_at, seconds=False) or "",
                has_personal_key=key is not None,
                provider=key.provider if key else None,
                model=key.model if key else None,
                key_last4=key.key_last4 if key else None,
                pending_password_requests=pending.get(user.id, 0),
                disabled_at=to_display(user.disabled_at, seconds=False),
                disabled_reason=user.disabled_reason,
            )
        )
    return result


def build_user_detail(session: Session, user: User, now: datetime) -> AdminUserDetail:
    base = build_users(session, [user])[0]
    tasks = session.execute(
        select(GenerationTask, User.username, Question.content_md)
        .join(User, GenerationTask.user_id == User.id)
        .outerjoin(Question, GenerationTask.question_id == Question.id)
        .where(GenerationTask.user_id == user.id)
        .order_by(GenerationTask.created_at.desc())
        .limit(3)
    ).all()
    requests = session.scalars(
        select(PasswordResetRequest)
        .where(PasswordResetRequest.user_id == user.id)
        .order_by(PasswordResetRequest.created_at.desc())
        .limit(3)
    ).all()
    return AdminUserDetail(
        **base.model_dump(),
        recent_tasks=[
            build_task(task, username, content, now) for task, username, content in tasks
        ],
        password_requests=[build_password_request(session, row) for row in requests],
    )


def build_task(
    task: GenerationTask,
    username: str,
    question_md: str | None,
    now: datetime | None = None,
) -> AdminTask:
    now = now or utcnow()
    return AdminTask(
        id=task.id,
        code=f"T-{task.id}",
        question_id=task.question_id,
        user_id=task.user_id,
        question=_excerpt(question_md),
        username=username,
        stage=task.stage,
        target_index=task.target_index,
        status=task.status,
        error_code=task.error_code,
        error_message=task.error_message,
        retry_index=task.retry_index,
        created_at=to_display(task.created_at) or "",
        started_at=to_display(task.started_at),
        finished_at=to_display(task.finished_at),
        duration=fmt_task_duration(
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            now=now,
        ),
    )


def build_task_detail(
    task: GenerationTask,
    username: str,
    question_md: str | None,
    now: datetime | None = None,
) -> AdminTaskDetail:
    base = build_task(task, username, question_md, now)
    timeline = [
        TaskTimelineItem(
            key="created",
            title="任务入队",
            status="queued",
            time=to_display(task.created_at) or "",
            meta=f"第 {task.retry_index} 次重试" if task.retry_index else None,
        )
    ]
    if task.started_at is not None:
        timeline.append(
            TaskTimelineItem(
                key="started",
                title="开始执行",
                status="running",
                time=to_display(task.started_at) or "",
                meta=None,
            )
        )
    if task.finished_at is not None:
        titles = {
            "done": "生成完成",
            "failed": "执行失败",
            "canceled": "已取消",
        }
        timeline.append(
            TaskTimelineItem(
                key="finished",
                title=titles.get(task.status, "已结束"),
                status=task.status,
                time=to_display(task.finished_at) or "",
                meta=task.error_code,
            )
        )
    return AdminTaskDetail(**base.model_dump(), timeline=timeline)


def build_ai_log(log: AiCallLog, username: str | None) -> AiLog:
    return AiLog(
        id=log.id,
        time=to_display(log.created_at) or "",
        username=username or "",
        operation=log.operation,
        model=log.model,
        prompt_version=log.prompt_version,
        status=log.status,
        latency=fmt_latency(log.latency_ms),
        queue_wait=fmt_latency(log.queue_wait_ms),
        tokens=fmt_tokens(log.input_tokens, log.output_tokens),
        input_tokens=log.input_tokens,
        output_tokens=log.output_tokens,
        key_source=log.key_source,
        error_code=log.error_code,
        question_id=log.question_id,
        has_raw=log.raw_response is not None,
    )


def build_audit(log: AdminAuditLog) -> AuditLog:
    return AuditLog(
        id=log.id,
        time=to_display(log.created_at) or "",
        admin=log.actor_username or "系统",
        action=log.action,
        target=log.target_label or log.target_id or "",
        target_type=log.target_type,
        target_id=log.target_id,
        reason=log.reason,
        result=log.result,
        ip=log.ip,
        request_id=log.request_id,
        before=log.before_json,
        after=log.after_json,
        error_message=log.after_json.get("error") if log.after_json else None,
    )


def build_password_request(session: Session, row: PasswordResetRequest) -> PasswordRequest:
    user = session.get(User, row.user_id)
    registered = (user.email or "") if user is not None else ""
    submitted = row.submitted_email
    return PasswordRequest(
        id=row.id,
        username=row.username,
        email=submitted,
        registered_email=registered,
        email_matches=bool(
            submitted and registered and submitted.lower() == registered.lower()
        ),
        account_status=(
            "disabled" if user is not None and user.disabled_at is not None else "active"
        ),
        reason=row.reason,
        status=row.status,
        submitted_at=to_display(row.created_at, seconds=False) or "",
        reviewed_by=row.reviewed_by,
        reviewed_at=to_display(row.reviewed_at, seconds=False),
        review_note=row.review_note,
        ip=row.ip,
        expires_at=to_display(row.expires_at, seconds=False),
        delivery_channel=row.delivery_channel,
        must_change_password=bool(user.must_change_password) if user else False,
        used_at=to_display(row.used_at, seconds=False),
    )
