"""管理端概览 / 告警 / 系统健康（ADM-003 / ADM-011）。

全部从真实表聚合，不写死环境、不编造事件；指标口径以 28 号文档 §8 与
admin/API_CONTRACT.md §2/§9/§10 为准。
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.models import (
    AdminAlertAck,
    AdminAuditLog,
    AiCallLog,
    GeneratedQuestion,
    GenerationTask,
    PasswordResetRequest,
    PracticeRecord,
    Question,
    User,
)
from app.schemas.admin import (
    AdminOverview,
    AdminSystem,
    AlertItem,
    AlertTarget,
    OverviewAiStats,
    OverviewContentStats,
    OverviewPasswordStats,
    OverviewStats,
    OverviewTaskStats,
    OverviewTrend,
    OverviewUserStats,
    SystemCheck,
    SystemConfigRow,
    SystemEnvironment,
    SystemEvent,
    SystemStatus,
    TrendPoint,
)
from app.services import admin_serializers
from app.utils.admin_time import (
    display_day,
    local_day_start_utc,
    to_display,
)

ALERT_THRESHOLDS = {
    "tasks_failed": 3,  # 最近 15 分钟失败任务数
    "ai_latency_p95_ms": 45_000,  # 最近 1 小时 P95
    "ai_error_rate_pct": 10.0,  # 最近 1 小时 error+invalid 占比
}


def _scalar_count(session: Session, stmt) -> int:
    return int(session.scalar(stmt) or 0)


def _percentile(sorted_values: list[int], pct: float) -> int:
    """最近秩法；空列表返回 0。"""
    if not sorted_values:
        return 0
    index = min(len(sorted_values) - 1, max(0, math.ceil(pct / 100 * len(sorted_values)) - 1))
    return sorted_values[index]


def _rate(part: int, total: int) -> float:
    return round(part * 100 / total, 1) if total else 0.0


def _ai_rows(session: Session, since: datetime):
    return session.execute(
        select(
            AiCallLog.status,
            AiCallLog.latency_ms,
            AiCallLog.input_tokens,
            AiCallLog.output_tokens,
            AiCallLog.created_at,
        ).where(AiCallLog.created_at >= since)
    ).all()


def _overview_ai(session: Session, now: datetime) -> tuple[OverviewAiStats, OverviewTrend]:
    since_24h = now - timedelta(hours=24)
    rows = _ai_rows(session, since_24h)
    total = len(rows)
    success = sum(1 for row in rows if row.status == "success")
    errors = sum(1 for row in rows if row.status == "error")
    invalid = sum(1 for row in rows if row.status == "invalid")
    latencies = sorted(row.latency_ms for row in rows if row.latency_ms is not None)
    stats = OverviewAiStats(
        calls_24h=total,
        success_rate=_rate(success, total),
        error_rate=_rate(errors, total),
        invalid_rate=_rate(invalid, total),
        p50_latency_ms=_percentile(latencies, 50),
        p95_latency_ms=_percentile(latencies, 95),
        input_tokens=sum(row.input_tokens or 0 for row in rows),
        output_tokens=sum(row.output_tokens or 0 for row in rows),
        estimated_cost=None,  # 没有价格配置时不编造金额（交接单 §12）
    )

    # 趋势：最近 7 个自然日（UTC+8），每天成功率与 P95 延迟
    start = local_day_start_utc(now) - timedelta(days=6)
    trend_rows = _ai_rows(session, start)
    success_trend: list[TrendPoint] = []
    latency_trend: list[TrendPoint] = []
    for offset in range(7):
        day_start = start + timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        bucket = [row for row in trend_rows if day_start <= row.created_at < day_end]
        ok = sum(1 for row in bucket if row.status == "success")
        day_latencies = sorted(
            row.latency_ms for row in bucket if row.latency_ms is not None
        )
        label = display_day(day_start)
        success_trend.append(TrendPoint(label=label, value=_rate(ok, len(bucket))))
        latency_trend.append(
            TrendPoint(
                label=label,
                value=round(_percentile(day_latencies, 95) / 1000, 1),
            )
        )
    return stats, OverviewTrend(success=success_trend, latency=latency_trend)


def _overview_tasks(session: Session, now: datetime) -> OverviewTaskStats:
    def count_by(status: str) -> int:
        return _scalar_count(
            session,
            select(func.count())
            .select_from(GenerationTask)
            .where(GenerationTask.status == status),
        )

    since_24h = now - timedelta(hours=24)
    done_24h = _scalar_count(
        session,
        select(func.count())
        .select_from(GenerationTask)
        .where(
            GenerationTask.status == "done",
            GenerationTask.finished_at.is_not(None),
            GenerationTask.finished_at >= since_24h,
        ),
    )
    canceled_24h = _scalar_count(
        session,
        select(func.count())
        .select_from(GenerationTask)
        .where(
            GenerationTask.status == "canceled",
            GenerationTask.finished_at.is_not(None),
            GenerationTask.finished_at >= since_24h,
        ),
    )
    oldest_queued = session.scalar(
        select(func.min(GenerationTask.created_at)).where(
            GenerationTask.status == "queued"
        )
    )
    oldest_seconds = (
        int((now - oldest_queued).total_seconds()) if oldest_queued is not None else 0
    )
    return OverviewTaskStats(
        queued=count_by("queued"),
        running=count_by("running"),
        failed=count_by("failed"),
        done_24h=done_24h,
        canceled_24h=canceled_24h,
        oldest_queue_seconds=max(oldest_seconds, 0),
    )


def _overview_users(session: Session, now: datetime) -> OverviewUserStats:
    total = _scalar_count(
        session,
        select(func.count()).select_from(User).where(User.role == "student"),
    )
    disabled = _scalar_count(
        session,
        select(func.count())
        .select_from(User)
        .where(User.role == "student", User.disabled_at.is_not(None)),
    )
    new_7d = _scalar_count(
        session,
        select(func.count())
        .select_from(User)
        .where(User.role == "student", User.created_at >= now - timedelta(days=7)),
    )
    return OverviewUserStats(
        total=total, active=total - disabled, disabled=disabled, new_7d=new_7d
    )


def _overview_content(session: Session) -> OverviewContentStats:
    def count(model, *conditions) -> int:
        return _scalar_count(
            session, select(func.count()).select_from(model).where(*conditions)
        )

    return OverviewContentStats(
        questions=count(Question, Question.deleted_at.is_(None)),
        generated=count(GeneratedQuestion, GeneratedQuestion.deleted_at.is_(None)),
        practice=count(PracticeRecord),
        # ADM-006 之前还没有标记载体；返回真实 0，不占位造数
        flagged=0,
        hidden=count(Question, Question.status == "hidden", Question.deleted_at.is_(None)),
    )


def _overview_password(session: Session, now: datetime) -> OverviewPasswordStats:
    today = local_day_start_utc(now)

    def count(*conditions) -> int:
        return _scalar_count(
            session,
            select(func.count()).select_from(PasswordResetRequest).where(*conditions),
        )

    return OverviewPasswordStats(
        pending=count(PasswordResetRequest.status == "pending"),
        approved_today=count(
            PasswordResetRequest.status == "approved",
            PasswordResetRequest.reviewed_at.is_not(None),
            PasswordResetRequest.reviewed_at >= today,
        ),
        rejected_today=count(
            PasswordResetRequest.status == "rejected",
            PasswordResetRequest.reviewed_at.is_not(None),
            PasswordResetRequest.reviewed_at >= today,
        ),
    )


def build_alerts(session: Session, now: datetime) -> list[AlertItem]:
    """四个告警由真实数据推导；条件不成立就不返回。"""
    alerts: list[AlertItem] = []
    acks = {row.alert_key: row for row in session.scalars(select(AdminAlertAck))}

    def make(
        key: str,
        *,
        severity: str,
        title: str,
        detail: str,
        rule: str,
        current: int,
        threshold: int,
        target: AlertTarget,
    ) -> AlertItem:
        ack = acks.get(key)
        return AlertItem(
            id=key,
            severity=severity,
            title=title,
            detail=detail,
            time=to_display(now, seconds=False) or "",
            status="acknowledged" if ack is not None else "active",
            acknowledged_by=ack.acknowledged_by if ack else None,
            acknowledged_at=to_display(ack.acknowledged_at, seconds=False) if ack else None,
            rule=rule,
            current=current,
            threshold=threshold,
            target=target,
        )

    # 最近 15 分钟失败任务
    since = now - timedelta(minutes=15)
    failed = session.execute(
        select(GenerationTask.created_at, GenerationTask.id)
        .where(
            GenerationTask.status == "failed",
            GenerationTask.created_at >= since,
        )
        .order_by(GenerationTask.created_at)
    ).all()
    if len(failed) >= ALERT_THRESHOLDS["tasks_failed"]:
        earliest = to_display(failed[0].created_at, seconds=False)
        alerts.append(
            make(
                "tasks_failed",
                severity="critical",
                title=f"{len(failed)} 个任务连续失败",
                detail=f"最近 15 分钟有 {len(failed)} 个任务失败，最早 {earliest}。",
                rule=f"最近 15 分钟失败任务 ≥ {ALERT_THRESHOLDS['tasks_failed']}",
                current=len(failed),
                threshold=ALERT_THRESHOLDS["tasks_failed"],
                target=AlertTarget(type="task", label="任务中心", to="/tasks?status=failed"),
            )
        )

    pending = _scalar_count(
        session,
        select(func.count())
        .select_from(PasswordResetRequest)
        .where(PasswordResetRequest.status == "pending"),
    )
    if pending > 0:
        alerts.append(
            make(
                "password_pending",
                severity="warning",
                title=f"{pending} 条密码申请待审批",
                detail=f"有 {pending} 条学生密码重置申请等待处理。",
                rule="待审批密码申请 > 0",
                current=pending,
                threshold=1,
                target=AlertTarget(
                    type="password_request", label="密码申请", to="/password-requests"
                ),
            )
        )

    hour_ago = now - timedelta(hours=1)
    recent = _ai_rows(session, hour_ago)
    latencies = sorted(row.latency_ms for row in recent if row.latency_ms is not None)
    p95 = _percentile(latencies, 95)
    if p95 > ALERT_THRESHOLDS["ai_latency_p95_ms"]:
        alerts.append(
            make(
                "ai_latency",
                severity="warning",
                title="AI 延迟偏高",
                detail=f"最近 1 小时 P95 延迟 {p95 / 1000:.1f}s，超过 45s。",
                rule="最近 1 小时 AI 调用 P95 > 45s",
                current=p95,
                threshold=ALERT_THRESHOLDS["ai_latency_p95_ms"],
                target=AlertTarget(type="ai_log", label="AI 日志", to="/ai-logs"),
            )
        )

    if recent:
        bad = sum(1 for row in recent if row.status in ("error", "invalid"))
        error_rate = _rate(bad, len(recent))
        if error_rate > ALERT_THRESHOLDS["ai_error_rate_pct"]:
            alerts.append(
                make(
                    "ai_error_rate",
                    severity="critical",
                    title="AI 失败率偏高",
                    detail=f"最近 1 小时 {len(recent)} 次调用中 {bad} 次失败（{error_rate}%）。",
                    rule="最近 1 小时 error+invalid 占比 > 10%",
                    current=bad,
                    threshold=ALERT_THRESHOLDS["ai_error_rate_pct"],
                    target=AlertTarget(type="ai_log", label="AI 日志", to="/ai-logs"),
                )
            )
    return alerts


def build_overview(session: Session, now: datetime | None = None) -> AdminOverview:
    now = now or utcnow()
    ai_stats, trend = _overview_ai(session, now)
    failed_tasks = session.execute(
        select(GenerationTask, User.username, Question.content_md)
        .join(User, GenerationTask.user_id == User.id)
        .outerjoin(Question, GenerationTask.question_id == Question.id)
        .where(GenerationTask.status == "failed")
        .order_by(GenerationTask.created_at.desc())
        .limit(5)
    ).all()
    pending_requests = session.scalars(
        select(PasswordResetRequest)
        .where(PasswordResetRequest.status == "pending")
        .order_by(PasswordResetRequest.created_at.desc())
        .limit(5)
    ).all()
    recent_audit = session.scalars(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(5)
    ).all()

    return AdminOverview(
        generated_at=to_display(now) or "",
        stats=OverviewStats(
            users=_overview_users(session, now),
            content=_overview_content(session),
            ai=ai_stats,
            tasks=_overview_tasks(session, now),
            password_requests=_overview_password(session, now),
        ),
        failed_tasks=[
            admin_serializers.build_task(task, username, content, now)
            for task, username, content in failed_tasks
        ],
        pending_password_requests=[
            admin_serializers.build_password_request(session, row)
            for row in pending_requests
        ],
        recent_audit=[admin_serializers.build_audit(row) for row in recent_audit],
        alerts=build_alerts(session, now),
        trend=trend,
    )


def build_system(session: Session, now: datetime | None = None) -> AdminSystem:
    now = now or utcnow()
    alerts = build_alerts(session, now)

    # 数据库探活：真的执行一次 SELECT 1 并计时
    started = time.perf_counter()
    session.execute(text("SELECT 1"))
    db_ms = max(int((time.perf_counter() - started) * 1000), 1)

    queued = _scalar_count(
        session,
        select(func.count()).select_from(GenerationTask).where(
            GenerationTask.status == "queued"
        ),
    )
    running = _scalar_count(
        session,
        select(func.count()).select_from(GenerationTask).where(
            GenerationTask.status == "running"
        ),
    )
    failed_24h = _scalar_count(
        session,
        select(func.count()).select_from(GenerationTask).where(
            GenerationTask.status == "failed",
            GenerationTask.created_at >= now - timedelta(hours=24),
        ),
    )

    llm_mode = "mock" if settings.llm_mock else "real"
    llm_configured = settings.llm_mock or bool(settings.llm_api_key)
    worker_check = "ok" if settings.task_workers_enabled else "warning"

    checks = [
        SystemCheck(
            key="api",
            name="API 网关",
            status="ok",
            value="正常",
            detail="管理 API 已响应",
            checked_at=to_display(now) or "",
            meta="探活",
        ),
        SystemCheck(
            key="database",
            name="数据库",
            status="ok",
            value=f"{db_ms} ms",
            detail="SELECT 1 通过",
            checked_at=to_display(now) or "",
            meta="探活",
        ),
        SystemCheck(
            key="worker",
            name="任务队列",
            status=worker_check,
            value=f"运行 {running} · 并发 {settings.task_max_concurrency}",
            detail=f"排队 {queued} · 24h 失败 {failed_24h}",
            checked_at=to_display(now) or "",
            meta="快照",
        ),
        SystemCheck(
            key="llm",
            name="大模型服务",
            status="ok" if llm_configured else "warning",
            value=llm_mode,
            detail=(
                "LLM_MOCK=true，不调用真实模型"
                if settings.llm_mock
                else f"模型 {settings.llm_model}"
            ),
            checked_at=to_display(now) or "",
            meta="配置",
        ),
    ]

    # 真实事件：最近任务 / 失败 AI 调用 / 审计，按时间合并取 5 条
    events: list[tuple[datetime, SystemEvent]] = []
    for task in session.scalars(
        select(GenerationTask).order_by(GenerationTask.created_at.desc()).limit(3)
    ):
        events.append(
            (
                task.created_at,
                SystemEvent(
                    time=to_display(task.created_at) or "",
                    title=f"任务 T-{task.id} {task.status}",
                    detail=f"{task.stage} 段 · 用户 {task.user_id}",
                    level="ok" if task.status == "done" else "warning",
                ),
            )
        )
    for log in session.scalars(
        select(AiCallLog)
        .where(AiCallLog.status != "success")
        .order_by(AiCallLog.created_at.desc())
        .limit(3)
    ):
        events.append(
            (
                log.created_at,
                SystemEvent(
                    time=to_display(log.created_at) or "",
                    title=f"AI {log.operation} {log.status}",
                    detail=log.error_code or "无错误码",
                    level="warning",
                ),
            )
        )
    for audit in session.scalars(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(3)
    ):
        events.append(
            (
                audit.created_at,
                SystemEvent(
                    time=to_display(audit.created_at) or "",
                    title=audit.action,
                    detail=audit.actor_username or "系统",
                    level="ok" if audit.result == "success" else "warning",
                ),
            )
        )
    events.sort(key=lambda item: item[0], reverse=True)

    levels = {alert.severity for alert in alerts}
    level = "critical" if "critical" in levels else ("warning" if levels else "ok")
    summary = {
        "ok": "运行正常",
        "warning": "有告警待处理",
        "critical": "存在严重告警",
    }[level]

    return AdminSystem(
        generated_at=to_display(now) or "",
        environment=SystemEnvironment(
            app_env=settings.app_env,
            is_demo=settings.app_env in ("development", "local") or settings.llm_mock,
            version=settings.version,
            llm_mode=llm_mode,
            worker_enabled=settings.task_workers_enabled,
            database=session.get_bind().dialect.name,
        ),
        status=SystemStatus(
            level=level, summary=summary, active_alerts=len(alerts)
        ),
        checks=checks,
        config=[
            SystemConfigRow(label="应用版本", value=settings.version, note="build 未注入"),
            SystemConfigRow(label="运行环境", value=settings.app_env, note="APP_ENV"),
            SystemConfigRow(
                label="任务并发",
                value=str(settings.task_max_concurrency),
                note="TASK_MAX_CONCURRENCY",
            ),
            SystemConfigRow(label="模型", value=settings.llm_model, note="LLM_MODEL"),
            SystemConfigRow(
                label="管理员 token",
                value=f"{settings.admin_token_expire_hours} 小时",
                note="ADMIN_TOKEN_EXPIRE_HOURS",
            ),
        ],
        events=[event for _, event in events[:5]],
    )
