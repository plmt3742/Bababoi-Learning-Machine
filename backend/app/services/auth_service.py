"""注册/登录业务（05 §6.3）：查重、验密、失败限流、更新 last_login_at。

限流计数交给 `core/rate_limit`（limits 的 MovingWindow）。默认进程内存存储，
只对单实例成立；多实例时把 `RATE_LIMIT_STORAGE_URL` 换成 redis:// 即可。
"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.core.rate_limit import SlidingWindowLimiter
from app.core.security import hash_password, verify_password
from app.db.base import utcnow
from app.models import User
from app.schemas.auth import RegisterRequest


class LoginRateLimiter:
    """按 IP 记录最近的登录失败；窗口内失败达到上限后拒绝该 IP 的登录。

    计数与过期清理交给 `core/rate_limit`（limits 的 MovingWindow 存储，内部自带锁），
    这里只保留登录特有的"失败才记账"语义。
    """

    def __init__(self, limit: int, window_s: int) -> None:
        self._limiter = SlidingWindowLimiter(
            f"{limit}/{window_s} seconds",
            code=ErrorCode.AUTH_RATE_LIMITED,
            message="登录失败次数过多，请稍后再试",
        )

    def check(self, ip: str) -> None:
        # 标识符带业务命名空间：`limits` 的 key 只拼 identifiers+额度，两个限流器
        # 配成同一额度时（如登录放松成 30/3600 或注册收紧成 5/60）没这个前缀
        # 会在 Redis 多实例下共用同一个桶
        self._limiter.check("login", ip)

    def record_failure(self, ip: str) -> None:
        self._limiter.record("login", ip)

    def reset(self, ip: str) -> None:
        self._limiter.reset("login", ip)

    def clear(self) -> None:
        """清空全部计数；测试复位用。"""
        self._limiter.clear()


# 模块级实例：进程内共享；测试里 clear() 复位
login_limiter = LoginRateLimiter(settings.login_rate_limit, settings.login_rate_window_s)
# 注册按 IP 限额（反复注册可以绕过"按用户"的 AI 额度，必须单独挡）
register_limiter = SlidingWindowLimiter(
    f"{settings.register_rate_limit}/{settings.register_rate_window_s} seconds",
    code=ErrorCode.AUTH_RATE_LIMITED,
    message="注册过于频繁，请稍后再试",
)


def register(session: Session, data: RegisterRequest, ip: str) -> User:
    exists = session.scalar(select(User).where(User.username == data.username))
    if exists is not None:
        raise ApiError(ErrorCode.USERNAME_TAKEN, "用户名已被占用", 409)

    # 扣额度放在重名检查之后：实验室全班共用一个出口 IP，
    # 一个人把用户名打错重试几次，不该吃掉全班的名额。
    # 标识符带业务命名空间，别和登录失败共用一个桶（见 LoginRateLimiter）
    register_limiter.hit("register", ip)
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
    # BE-028：单会话策略——版本号 +1 后，其他设备手里的旧 token 立刻失效。
    # 用 SQL 表达式自增而不是"读出来 +1 再写回"：两个并发登录也能各自拿到新版本，
    # 结果稳定是"最后一次登录生效"，不会出现两个 token 同时有效。
    session.execute(
        update(User).where(User.id == user.id).values(token_version=User.token_version + 1)
    )
    session.commit()
    session.refresh(user)
    return user


def logout(session: Session, user_id: int) -> None:
    """吊销该账号当前的会话（BE-028）：版本号 +1，手里的 token 下一次请求即 401。

    幂等：重复调用只是多 +1，没有副作用。
    """
    session.execute(
        update(User).where(User.id == user_id).values(token_version=User.token_version + 1)
    )
    session.commit()
