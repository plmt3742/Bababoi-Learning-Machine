"""密码散列与 JWT 签发/校验（05 §6.3 / §9.4）。

只做密码和 token 两件事；用户查库、限流这些业务在 auth_service。
"""
from __future__ import annotations

from datetime import timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow

# bcrypt 算法只取前 72 字节，超长部分静默丢弃——与其让长密码"看起来能登录"
# 实际散列的是截断值，不如在入口就拒掉
PASSWORD_MAX_BYTES = 72


def _secret() -> str:
    if len(settings.jwt_secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "JWT_SECRET 未配置或不足 32 字节（05 §9.4），拒绝签发/校验 token"
        )
    return settings.jwt_secret


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # 库里存了坏数据（空串/非 bcrypt 格式）时按"不匹配"处理，不让 500 漏出去
        return False


def create_access_token(user_id: int) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.access_token_expire_days),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_access_token(token: str) -> int:
    """校验并取出 user_id；过期与其他非法 token 用不同错误码（05 §6.2）。"""
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ApiError(
            ErrorCode.AUTH_TOKEN_EXPIRED, "登录已过期，请重新登录", 401
        ) from None
    except jwt.InvalidTokenError:
        raise ApiError(
            ErrorCode.AUTH_INVALID_CREDENTIALS, "无效的登录凭证", 401
        ) from None
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise ApiError(
            ErrorCode.AUTH_INVALID_CREDENTIALS, "无效的登录凭证", 401
        ) from None
