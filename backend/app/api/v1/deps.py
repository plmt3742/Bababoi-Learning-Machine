"""跨路由的 FastAPI 依赖：拿当前登录用户。

放 api 包而不是 core：它要查库，属于路由层依赖，不是纯工具。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import ApiError, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User

# auto_error=False：缺 header 时默认会抛 403，而我们的信封统一用 401
_bearer = HTTPBearer(auto_error=False)

F = TypeVar("F", bound=Callable)


def exempt_password_gate(fn: F) -> F:  # noqa: UP047 - 保持 Callable 泛型，改 PEP 695 无收益
    """标在端点上：`must_change_password=true` 时仍允许访问。

    白名单只有三个（少一个就是死锁）：/auth/me 读标记、/auth/change-password 改密、
    /auth/logout 退出。用端点标记而不是路径匹配——换前缀不会失灵，代码上也看得出谁被豁免。
    """
    fn.__password_gate_exempt__ = True  # type: ignore[attr-defined]
    return fn


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    """所有需要登录的端点都挂这个依赖；拿到的 user 一定存在。"""
    if credentials is None:
        raise ApiError(ErrorCode.AUTH_INVALID_CREDENTIALS, "缺少登录凭证", 401)

    user_id, version = decode_access_token(credentials.credentials)
    user = session.get(User, user_id)
    if user is None:
        # token 有效但用户已不存在（如换了数据库）——按凭证无效处理
        raise ApiError(ErrorCode.AUTH_INVALID_CREDENTIALS, "无效的登录凭证", 401)
    if version != user.token_version:
        # BE-028：只有改密/强制下线会把 token_version +1，旧会话在这里失效；
        # 登录/登出不动版本（多设备共存）。复用 AUTH_TOKEN_EXPIRED：
        # 前端本来就是"401 清 token 回登录页"，不需要新码。
        raise ApiError(ErrorCode.AUTH_TOKEN_EXPIRED, "登录已失效，请重新登录", 401)
    if user.disabled_at is not None:
        # ADM-009：禁用是软状态，token 仍有效但一律拒绝；单独错误码便于前端提示。
        raise ApiError(ErrorCode.ACCOUNT_DISABLED, "账号已被禁用", 403)
    if user.must_change_password:
        # BE-030：门禁放全局默认拒绝，新增端点天然受保护；白名单端点自带标记。
        endpoint = request.scope.get("endpoint")
        if not getattr(endpoint, "__password_gate_exempt__", False):
            raise ApiError(
                ErrorCode.PASSWORD_CHANGE_REQUIRED,
                "首次登录需先修改密码",
                403,
            )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """所有 `/admin/*`（登录除外）挂这个依赖。

    角色每次都查 DB——JWT 里不带 role，也不允许以后往里加：token 是 7 天免签的，
    claim 里的角色会在管理员被降级后继续生效。禁用检查已在 get_current_user 里。
    """
    if user.role != "admin":
        raise ApiError(ErrorCode.ADMIN_REQUIRED, "需要管理员权限", 403)
    return user


def get_session_factory(session: Session = Depends(get_session)) -> sessionmaker:
    """给"要在请求之外再开一个短事务"的地方用的工厂（识图写 ai_call_logs，05 §9.3）。

    为什么从注入的 session 反推 engine，而不是直接用 `db.session.SessionLocal`：
    测试把 `get_session` 换成临时库，真实 SessionLocal 还指着仓库里的 .db——
    直接用的话识图的日志会写进测试没在看的库，测试隔离被悄悄打破。
    """
    return sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
