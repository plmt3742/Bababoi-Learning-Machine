"""认证路由（05 §6.3）：register / login / logout / change-password / me，都是薄壳。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_session
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service
from app.utils.client_ip import client_ip


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.token_version),
        user=UserResponse.model_validate(user),
    )


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    data: RegisterRequest, request: Request, session: Session = Depends(get_session)
) -> TokenResponse:
    return _token_response(auth_service.register(session, data, client_ip(request)))


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest, request: Request, session: Session = Depends(get_session)
) -> TokenResponse:
    user = auth_service.login(session, client_ip(request), data.username, data.password)
    return _token_response(user)


@router.post("/logout", status_code=204)
def logout(user: User = Depends(get_current_user)) -> None:
    """登出只清前端 token，服务端**不吊销**（定案单 2026-11-21 §3）。

    token_version 是"整账号作废"的粗粒度开关：登出若也 +1，手机上点一下退出，
    电脑会跟着掉线。要"只失效当前设备"得加 jti + 黑名单，属 P2。
    """
    return None


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """凭旧密码改密（BE-029）：成功后版本 +1，所有设备（含当前）需重新登录。"""
    auth_service.change_password(session, user, body.current_password, body.new_password)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
