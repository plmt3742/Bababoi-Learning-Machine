"""审计写入（ADM-009 / 28 号文档 §6.3）。

约定：
- 本模块只 `session.add`，**不 commit**。高风险写操作要求「操作与审计同一事务」，
  由业务方在同一次 commit 里落库；审计失败则整个操作回滚。
- 记录的是快照（用户名/目标标签），不存密码、临时密码、JWT、API Key、完整学生答案。
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AdminAuditLog, User
from app.utils.client_ip import client_ip

_USER_AGENT_MAX = 255


def record(
    session: Session,
    *,
    action: str,
    request: Request | None = None,
    actor: User | None = None,
    target_type: str | None = None,
    target_id: int | str | None = None,
    target_label: str | None = None,
    target_owner_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    result: str = "success",
) -> AdminAuditLog:
    """把一条审计挂到当前事务里，返回对象（id 在 commit 后才有）。

    `actor=None` 表示系统动作（如公开密码申请），此时 actor 字段留空。
    """
    log = AdminAuditLog(
        actor_user_id=actor.id if actor is not None else None,
        actor_username=actor.username if actor is not None else "",
        action=action,
        target_type=target_type,
        target_id=None if target_id is None else str(target_id),
        target_label=target_label,
        target_owner_id=target_owner_id,
        before_json=before,
        after_json=after,
        reason=reason,
        result=result,
        request_id=getattr(request.state, "request_id", "") if request is not None else "",
        ip=client_ip(request) if request is not None else "",
        user_agent=(
            (request.headers.get("user-agent") or "")[:_USER_AGENT_MAX]
            if request is not None
            else ""
        ),
    )
    session.add(log)
    return log
