"""管理端请求/响应结构（ADM-002 起）。

命名按 `admin/src/types.ts` 原样落地：
- `AdminProfile`、概览 `stats` 内部计数、列表分页 `page_size` 是 snake_case；
- 其余列表 DTO 是 camelCase（前端 10k 行已按此写完），用别名生成器在出口转换。
后端内部一律 snake_case，别名只存在于 Pydantic 边界。
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models import User

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AdminProfile(BaseModel):
    id: int
    username: str
    email: str
    role: str
    must_change_password: bool


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminProfile


def profile_from_user(user: User) -> AdminProfile:
    # 前端把 email 当 string 用；库里可空，出口统一空串，避免前端 .trim() 崩
    return AdminProfile(
        id=user.id,
        username=user.username,
        email=user.email or "",
        role=user.role,
        must_change_password=user.must_change_password,
    )


class Page(BaseModel, Generic[T]):  # noqa: UP046 - pydantic 泛型用 Generic[T] 更稳
    items: list[T]
    total: int
    page: int
    page_size: int


# --- 用户 -------------------------------------------------------------------


class AdminUser(CamelModel):
    id: int
    username: str
    email: str
    status: str  # active | disabled
    role: str
    questions: int
    generated: int
    practice: int
    last_login: str | None
    created_at: str
    has_personal_key: bool
    provider: str | None
    model: str | None
    key_last4: str | None
    pending_password_requests: int
    disabled_at: str | None
    disabled_reason: str | None


# --- 密码申请 ---------------------------------------------------------------


class PasswordRequest(CamelModel):
    id: int
    username: str
    email: str | None  # 学生提交的邮箱
    registered_email: str
    email_matches: bool
    account_status: str
    reason: str
    status: str
    submitted_at: str
    reviewed_by: str | None
    reviewed_at: str | None
    review_note: str | None
    ip: str
    expires_at: str | None
    delivery_channel: str | None
    must_change_password: bool


# --- 任务 -------------------------------------------------------------------


class AdminTask(CamelModel):
    id: int
    code: str
    question_id: int
    user_id: int
    question: str
    username: str
    stage: str
    target_index: int | None
    status: str
    error_code: str | None
    error_message: str | None
    retry_index: int
    created_at: str
    started_at: str | None
    finished_at: str | None
    duration: str


class TaskTimelineItem(CamelModel):
    key: str
    title: str
    status: str
    time: str
    meta: str | None


class AdminTaskDetail(AdminTask):
    timeline: list[TaskTimelineItem]


class AdminUserDetail(AdminUser):
    recent_tasks: list[AdminTask]
    password_requests: list[PasswordRequest]


# --- AI 日志 ----------------------------------------------------------------


class AiLog(CamelModel):
    id: int
    time: str
    username: str
    operation: str
    model: str | None
    prompt_version: str | None
    status: str
    latency: str
    queue_wait: str
    tokens: str
    input_tokens: int | None
    output_tokens: int | None
    key_source: str | None
    error_code: str | None
    question_id: int | None
    has_raw: bool


class AiLogRawResult(BaseModel):
    raw: str
    truncated: bool
    audit_id: int


# --- 审计 -------------------------------------------------------------------


class AuditLog(CamelModel):
    id: int
    time: str
    admin: str
    action: str
    target: str
    target_type: str | None
    target_id: str | None
    reason: str | None
    result: str
    ip: str
    request_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    error_message: str | None


# --- 告警 -------------------------------------------------------------------


class AlertTarget(CamelModel):
    type: str
    label: str
    to: str


class AlertItem(CamelModel):
    id: str
    severity: str
    title: str
    detail: str
    time: str
    status: str
    acknowledged_by: str | None
    acknowledged_at: str | None
    rule: str
    current: int
    threshold: int
    target: AlertTarget | None


# --- 概览（内部计数沿用 snake_case，与 types.ts 一致） -----------------------


class OverviewUserStats(BaseModel):
    total: int
    active: int
    disabled: int
    new_7d: int


class OverviewContentStats(BaseModel):
    questions: int
    generated: int
    practice: int
    flagged: int
    hidden: int


class OverviewAiStats(BaseModel):
    calls_24h: int
    success_rate: float
    error_rate: float
    invalid_rate: float
    p50_latency_ms: int
    p95_latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost: float | None


class OverviewTaskStats(BaseModel):
    queued: int
    running: int
    failed: int
    done_24h: int
    canceled_24h: int
    oldest_queue_seconds: int


class OverviewPasswordStats(BaseModel):
    pending: int
    approved_today: int
    rejected_today: int


class OverviewStats(BaseModel):
    users: OverviewUserStats
    content: OverviewContentStats
    ai: OverviewAiStats
    tasks: OverviewTaskStats
    password_requests: OverviewPasswordStats


class TrendPoint(BaseModel):
    label: str
    value: float


class OverviewTrend(BaseModel):
    success: list[TrendPoint]
    latency: list[TrendPoint]


class AdminOverview(BaseModel):
    generated_at: str
    stats: OverviewStats
    failed_tasks: list[AdminTask]
    pending_password_requests: list[PasswordRequest]
    recent_audit: list[AuditLog]
    alerts: list[AlertItem]
    trend: OverviewTrend


# --- 系统健康（混合命名按 types.ts） ----------------------------------------


class SystemEnvironment(BaseModel):
    app_env: str
    is_demo: bool
    version: str
    llm_mode: str
    worker_enabled: bool
    database: str


class SystemStatus(BaseModel):
    level: str
    summary: str
    active_alerts: int


class SystemCheck(CamelModel):
    key: str
    name: str
    status: str
    value: str
    detail: str
    checked_at: str
    meta: str


class SystemConfigRow(BaseModel):
    label: str
    value: str
    note: str


class SystemEvent(BaseModel):
    time: str
    title: str
    detail: str
    level: str


class AdminSystem(BaseModel):
    generated_at: str
    environment: SystemEnvironment
    status: SystemStatus
    checks: list[SystemCheck]
    config: list[SystemConfigRow]
    events: list[SystemEvent]


AdminUserDetail.model_rebuild()

