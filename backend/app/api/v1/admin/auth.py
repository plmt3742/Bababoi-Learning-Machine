"""管理员认证路由（ADM-002）：login / me / logout。

登录不挂 require_admin（它本身就是拿 token 的入口），其余两个必须管理员。
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


@router.get("/me", response_model=AdminProfile)
def me(user: User = Depends(require_admin)) -> AdminProfile:
    return profile_from_user(user)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> None:
    admin_auth_service.admin_logout(session, request, user)
