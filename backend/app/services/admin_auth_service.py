"""管理员登录/登出（ADM-002）。学生登录仍在 auth_service，不混用：
管理员要查角色、写审计、签发更短的 token，走独立函数比在 login() 里加分支清楚。
"""
from __future__ import annotations

import logging

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.core.rate_limit import SlidingWindowLimiter
from app.core.security import verify_password
from app.db.base import utcnow
from app.models import User
from app.services import audit_service
from app.utils.client_ip import client_ip

logger = logging.getLogger(__name__)

# 管理端登录单独一个桶：与学生登录共桶时，管理员输错 5 次会把同一出口 IP 的
# 全班学生锁 60 秒，反过来学生乱试也能把管理员挡在门外。
admin_login_limiter = SlidingWindowLimiter(
    f"{settings.login_rate_limit}/{settings.login_rate_window_s} seconds",
    code=ErrorCode.AUTH_RATE_LIMITED,
    message="登录失败次数过多，请稍后再试",
)
_ADMIN_LIMITER_NS = "admin-login"


def admin_login(
    session: Session, request: Request, username: str, password: str
) -> User:
    """凭用户名密码登录管理端；只允许 role=admin。

    失败口径：账号不存在/密码错误统一 401（不泄露账号是否存在）；密码正确但不是
    管理员或已被禁用返回 403。失败计数只进管理端自己的限流桶。
    """
    ip = client_ip(request)
    admin_login_limiter.check(_ADMIN_LIMITER_NS, ip)
    user = session.scalar(select(User).where(User.username == username))

    if user is None or not verify_password(password, user.password_hash):
        admin_login_limiter.record(_ADMIN_LIMITER_NS, ip)
        raise ApiError(
            ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误", 401
        )

    # 密码已正确，不记失败——用学生账号试管理端不该拖累管理端自己的桶
    if user.disabled_at is not None:
        raise ApiError(ErrorCode.ACCOUNT_DISABLED, "账号已被禁用", 403)
    if user.role != "admin":
        raise ApiError(ErrorCode.ADMIN_REQUIRED, "需要管理员权限", 403)

    admin_login_limiter.reset(_ADMIN_LIMITER_NS, ip)
    user.last_login_at = utcnow()
    audit_service.record(
        session, action="admin.login", request=request, actor=user, result="success"
    )
    session.commit()
    session.refresh(user)
    return user


def admin_logout(session: Session, request: Request, user: User) -> None:
    """登出审计 best-effort：审计写失败不影响登出（客户端清 token 即可）。"""
    try:
        audit_service.record(
            session, action="admin.logout", request=request, actor=user
        )
        session.commit()
    except Exception:  # noqa: BLE001 - 审计失败不能把登出变成 500
        session.rollback()
        logger.warning("admin.logout 审计写入失败，已忽略", exc_info=True)
