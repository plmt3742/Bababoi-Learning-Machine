"""注册/登录业务（05 §6.3）：查重、验密、失败限流、更新 last_login_at。

限流用进程内存计数——单实例部署（12号 §3.3 明确不引入 Redis）够用；
多实例部署时这里要换成 DB 计数，05 §6.3 也留了这个口子。
"""
from __future__ import annotations

import threading
from collections import deque
from time import monotonic

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.core.security import hash_password, verify_password
from app.db.base import utcnow
from app.models import User
from app.schemas.auth import RegisterRequest


class LoginRateLimiter:
    """按 IP 记录最近的登录失败时间；窗口内失败达到上限后拒绝该 IP 的登录。"""

    def __init__(self, limit: int, window_s: int) -> None:
        self.limit = limit
        self.window_s = window_s
        self._failures: dict[str, deque[float]] = {}
        # 同步端点跑在线程池里（05 §9.2），dict 读写要加锁
        self._lock = threading.Lock()

    def _prune(self, failures: deque[float], now: float) -> None:
        while failures and now - failures[0] > self.window_s:
            failures.popleft()

    def check(self, ip: str) -> None:
        with self._lock:
            failures = self._failures.get(ip)
            if not failures:
                return
            self._prune(failures, monotonic())
            if len(failures) >= self.limit:
                raise ApiError(
                    ErrorCode.AUTH_RATE_LIMITED,
                    "登录失败次数过多，请一分钟后再试",
                    429,
                )

    def record_failure(self, ip: str) -> None:
        with self._lock:
            failures = self._failures.setdefault(ip, deque())
            failures.append(monotonic())

    def reset(self, ip: str) -> None:
        with self._lock:
            self._failures.pop(ip, None)

    def clear(self) -> None:
        """清空全部计数；测试复位用。"""
        with self._lock:
            self._failures.clear()


# 模块级实例：进程内共享；测试里直接清空 _failures 即可复位
login_limiter = LoginRateLimiter(settings.login_rate_limit, settings.login_rate_window_s)


def register(session: Session, data: RegisterRequest) -> User:
    exists = session.scalar(select(User).where(User.username == data.username))
    if exists is not None:
        raise ApiError(ErrorCode.USERNAME_TAKEN, "用户名已被占用", 409)

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login(session: Session, ip: str, username: str, password: str) -> User:
    login_limiter.check(ip)
    user = session.scalar(select(User).where(User.username == username))

    # 用户不存在和密码错误返回同一个错误，不给撞库者"这个用户名存在"的信号
    if user is None or not verify_password(password, user.password_hash):
        login_limiter.record_failure(ip)
        raise ApiError(
            ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误", 401
        )

    login_limiter.reset(ip)
    user.last_login_at = utcnow()
    session.commit()
    session.refresh(user)
    return user
