"""管理端只读端点（ADM-003 / ADM-007 / ADM-011）。

整个 router 挂 `require_admin` 作为 router 级依赖：新增端点默认就是管理员专属，
不会因为漏写一个参数把数据裸奔出去。学生 token 403、禁用 403 在依赖里统一处理。
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.db.session import get_session
from app.models import (
    AdminAuditLog,
    AiCallLog,
    GenerationTask,
    PasswordResetRequest,
    Question,
    User,
)
from app.schemas.admin import (
    AdminOverview,
    AdminSystem,
    AdminTask,
    AdminTaskDetail,
    AdminUser,
    AdminUserDetail,
    AiLog,
    AlertItem,
    AuditLog,
    Page,
    PasswordRequest,
)
from app.services import admin_serializers, admin_stats_service
from app.services.admin_actions import actions_matching

router = APIRouter(dependencies=[Depends(require_admin)])

_PAGE_MAX = 100


def _paging(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), _PAGE_MAX)
    return page, page_size


def _like(column, keyword: str):
    return column.ilike(f"%{keyword}%")


# --- 概览 / 告警 / 系统 ------------------------------------------------------


@router.get("/overview", response_model=AdminOverview)
def overview(session: Session = Depends(get_session)) -> AdminOverview:
    return admin_stats_service.build_overview(session)


@router.get("/alerts", response_model=list[AlertItem])
def alerts(session: Session = Depends(get_session)) -> list[AlertItem]:
    return admin_stats_service.build_alerts(session, utcnow())


@router.get("/system", response_model=AdminSystem)
def system(session: Session = Depends(get_session)) -> AdminSystem:
    return admin_stats_service.build_system(session)


# --- 用户 -------------------------------------------------------------------


@router.get("/users", response_model=Page[AdminUser])
def list_users(
    q: str | None = Query(default=None, max_length=64),
    status: Literal["active", "disabled", "all"] = "all",
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
) -> Page[AdminUser]:
    page, page_size = _paging(page, page_size)
    conditions = [User.role == "student"]
    if status == "active":
        conditions.append(User.disabled_at.is_(None))
    elif status == "disabled":
        conditions.append(User.disabled_at.is_not(None))
    keyword = (q or "").strip()
    if keyword:
        conditions.append(
            or_(_like(User.username, keyword), _like(User.email, keyword))
        )

    total = int(
        session.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    )
    users = session.scalars(
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[AdminUser](
        items=admin_serializers.build_users(session, list(users)),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(
    user_id: int, session: Session = Depends(get_session)
) -> AdminUserDetail:
    user = session.get(User, user_id)
    # 管理端只管学生；管理员账号不出现在列表，也不允许按 id 探
    if user is None or user.role != "student":
        raise ApiError(ErrorCode.NOT_FOUND, "用户不存在", 404)
    return admin_serializers.build_user_detail(session, user, utcnow())


# --- 任务 -------------------------------------------------------------------


@router.get("/tasks", response_model=Page[AdminTask])
def list_tasks(
    status: Literal["queued", "running", "done", "failed", "canceled", "all"] = "all",
    q: str | None = Query(default=None, max_length=64),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
) -> Page[AdminTask]:
    page, page_size = _paging(page, page_size)
    conditions = []
    if status != "all":
        conditions.append(GenerationTask.status == status)
    keyword = (q or "").strip()
    if keyword:
        if keyword.upper().startswith("T-"):
            keyword = keyword[2:]
        conditions.append(
            or_(
                _like(cast(GenerationTask.id, String), keyword),
                _like(User.username, keyword),
                _like(Question.content_md, keyword),
                _like(GenerationTask.error_code, keyword),
                _like(GenerationTask.error_message, keyword),
            )
        )

    base = (
        select(GenerationTask, User.username, Question.content_md)
        .join(User, GenerationTask.user_id == User.id)
        .outerjoin(Question, GenerationTask.question_id == Question.id)
        .where(*conditions)
    )
    total = int(
        session.scalar(
            select(func.count())
            .select_from(
                select(GenerationTask.id)
                .join(User, GenerationTask.user_id == User.id)
                .outerjoin(Question, GenerationTask.question_id == Question.id)
                .where(*conditions)
                .subquery()
            )
        )
        or 0
    )
    rows = session.execute(
        base.order_by(GenerationTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    now = utcnow()
    return Page[AdminTask](
        items=[
            admin_serializers.build_task(task, username, content, now)
            for task, username, content in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}", response_model=AdminTaskDetail)
def get_task(
    task_id: int, session: Session = Depends(get_session)
) -> AdminTaskDetail:
    row = session.execute(
        select(GenerationTask, User.username, Question.content_md)
        .join(User, GenerationTask.user_id == User.id)
        .outerjoin(Question, GenerationTask.question_id == Question.id)
        .where(GenerationTask.id == task_id)
    ).first()
    if row is None:
        raise ApiError(ErrorCode.TASK_NOT_FOUND, "任务不存在", 404)
    task, username, content = row
    return admin_serializers.build_task_detail(task, username, content)


# --- AI 日志 ----------------------------------------------------------------


@router.get("/ai-logs", response_model=Page[AiLog])
def list_ai_logs(
    status: Literal["success", "error", "invalid", "all"] = "all",
    operation: Literal["vision", "analyze", "generate", "judge", "all"] = "all",
    q: str | None = Query(default=None, max_length=64),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
) -> Page[AiLog]:
    page, page_size = _paging(page, page_size)
    conditions = []
    if status != "all":
        conditions.append(AiCallLog.status == status)
    if operation != "all":
        conditions.append(AiCallLog.operation == operation)
    keyword = (q or "").strip()
    if keyword:
        conditions.append(
            or_(
                _like(cast(AiCallLog.id, String), keyword),
                _like(User.username, keyword),
                _like(AiCallLog.model, keyword),
                _like(AiCallLog.prompt_version, keyword),
                _like(AiCallLog.error_code, keyword),
            )
        )

    count_stmt = (
        select(func.count())
        .select_from(AiCallLog)
        .outerjoin(User, AiCallLog.user_id == User.id)
        .where(*conditions)
    )
    total = int(session.scalar(count_stmt) or 0)
    rows = session.execute(
        select(AiCallLog, User.username)
        .outerjoin(User, AiCallLog.user_id == User.id)
        .where(*conditions)
        .order_by(AiCallLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[AiLog](
        items=[admin_serializers.build_ai_log(log, username) for log, username in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/ai-logs/{log_id}", response_model=AiLog)
def get_ai_log(log_id: int, session: Session = Depends(get_session)) -> AiLog:
    row = session.execute(
        select(AiCallLog, User.username)
        .outerjoin(User, AiCallLog.user_id == User.id)
        .where(AiCallLog.id == log_id)
    ).first()
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND, "AI 调用记录不存在", 404)
    log, username = row
    return admin_serializers.build_ai_log(log, username)


# --- 审计 -------------------------------------------------------------------


@router.get("/audit", response_model=Page[AuditLog])
def list_audit(
    q: str | None = Query(default=None, max_length=64),
    result: Literal["success", "failed", "all"] = "all",
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
) -> Page[AuditLog]:
    page, page_size = _paging(page, page_size)
    conditions = []
    if result != "all":
        conditions.append(AdminAuditLog.result == result)
    keyword = (q or "").strip()
    if keyword:
        matches = [
            _like(AdminAuditLog.actor_username, keyword),
            _like(AdminAuditLog.action, keyword),
            _like(AdminAuditLog.target_label, keyword),
            _like(AdminAuditLog.target_id, keyword),
            _like(AdminAuditLog.reason, keyword),
            _like(AdminAuditLog.request_id, keyword),
            _like(AdminAuditLog.ip, keyword),
        ]
        # 中文动作名（如「通过密码申请」）也要能搜到
        codes = actions_matching(keyword)
        if codes:
            matches.append(AdminAuditLog.action.in_(codes))
        conditions.append(or_(*matches))

    total = int(
        session.scalar(
            select(func.count()).select_from(AdminAuditLog).where(*conditions)
        )
        or 0
    )
    rows = session.scalars(
        select(AdminAuditLog)
        .where(*conditions)
        .order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[AuditLog](
        items=[admin_serializers.build_audit(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit/{audit_id}", response_model=AuditLog)
def get_audit(audit_id: int, session: Session = Depends(get_session)) -> AuditLog:
    row = session.get(AdminAuditLog, audit_id)
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND, "审计记录不存在", 404)
    return admin_serializers.build_audit(row)


# --- 密码申请只读（审批在 ADM-010/BE-030） ----------------------------------


@router.get("/password-requests", response_model=Page[PasswordRequest])
def list_password_requests(
    status: Literal["pending", "approved", "rejected", "all"] = "all",
    q: str | None = Query(default=None, max_length=64),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
) -> Page[PasswordRequest]:
    page, page_size = _paging(page, page_size)
    conditions = []
    if status != "all":
        conditions.append(PasswordResetRequest.status == status)
    keyword = (q or "").strip()
    if keyword:
        conditions.append(
            or_(
                _like(PasswordResetRequest.username, keyword),
                _like(PasswordResetRequest.submitted_email, keyword),
                _like(PasswordResetRequest.reason, keyword),
            )
        )
    total = int(
        session.scalar(
            select(func.count())
            .select_from(PasswordResetRequest)
            .where(*conditions)
        )
        or 0
    )
    rows = session.scalars(
        select(PasswordResetRequest)
        .where(*conditions)
        .order_by(PasswordResetRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[PasswordRequest](
        items=[admin_serializers.build_password_request(session, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/password-requests/{request_id}", response_model=PasswordRequest)
def get_password_request(
    request_id: int, session: Session = Depends(get_session)
) -> PasswordRequest:
    row = session.get(PasswordResetRequest, request_id)
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND, "密码申请不存在", 404)
    return admin_serializers.build_password_request(session, row)
