"""管理员认证路由（ADM-002）：login / me / logout。

登录放在 public router（它本身就是拿 token 的入口）；me/logout 放受保护的子 router。
父 router 的默认 `require_admin` 见 `admin/__init__.py`，这里再显式声明一次是为了
拿到 user 对象，不是权限来源。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_session
from app.models import User
from app.schemas.admin import (
    AdminLoginRequest,
    AdminProfile,
    AdminTokenResponse,
    profile_from_user,
)
from app.services import admin_auth_service

router = APIRouter()
protected_router = APIRouter()


@router.post("/auth/login", response_model=AdminTokenResponse)
def login(
    data: AdminLoginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> AdminTokenResponse:
    user = admin_auth_service.admin_login(
        session, request, data.username, data.password
    )
    return AdminTokenResponse(
        access_token=create_access_token(
            user.id,
            user.token_version,
            expires_hours=settings.admin_token_expire_hours,
        ),
        user=profile_from_user(user),
    )


@protected_router.get("/me", response_model=AdminProfile)
def me(user: User = Depends(require_admin)) -> AdminProfile:
    return profile_from_user(user)


@protected_router.post("/logout", status_code=204)
def logout(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> None:
    admin_auth_service.admin_logout(session, request, user)
