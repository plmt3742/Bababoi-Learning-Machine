"""跨路由的 FastAPI 依赖：拿当前登录用户。

放 api 包而不是 core：它要查库，属于路由层依赖，不是纯工具。
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User

# auto_error=False：缺 header 时默认会抛 403，而我们的信封统一用 401
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    """所有需要登录的端点都挂这个依赖；拿到的 user 一定存在。"""
    if credentials is None:
        raise ApiError(ErrorCode.AUTH_INVALID_CREDENTIALS, "缺少登录凭证", 401)

    user_id = decode_access_token(credentials.credentials)
    user = session.get(User, user_id)
    if user is None:
        # token 有效但用户已不存在（如换了数据库）——按凭证无效处理
        raise ApiError(ErrorCode.AUTH_INVALID_CREDENTIALS, "无效的登录凭证", 401)
    return user
