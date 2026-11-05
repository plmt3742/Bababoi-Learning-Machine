"""认证路由（05 §6.3）：register / login / me，三个端点都是薄壳。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_session
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserResponse.model_validate(user)
    )


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    data: RegisterRequest, session: Session = Depends(get_session)
) -> TokenResponse:
    return _token_response(auth_service.register(session, data))


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest, request: Request, session: Session = Depends(get_session)
) -> TokenResponse:
    user = auth_service.login(session, _client_ip(request), data.username, data.password)
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
