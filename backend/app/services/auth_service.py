"""注册/登录/改密业务（05 §6.3）：查重、验密、失败限流、更新 last_login_at、会话版本吊销。

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
# 改密按账号限流（不需要 IP：请求已经带登录态）；只数失败，成功会清零。
# 独立建、不复用 LoginRateLimiter：标识符带 change-password 命名空间。
change_password_limiter = SlidingWindowLimiter(
    "5/60 seconds",
    code=ErrorCode.AUTH_RATE_LIMITED,
    message="改密尝试次数过多，请稍后再试",
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
    if user.disabled_at is not None:
        # ADM-009：被禁用的账号密码正确也不发 token；前端按 code 提示联系管理员
        raise ApiError(ErrorCode.ACCOUNT_DISABLED, "账号已被禁用", 403)
    user.last_login_at = utcnow()
    # 登录**不动** token_version：手机拍题 + 电脑做题是学生的真实形态，
    # 登录就 +1 会让两台设备互相踢下线（定案单 2026-11-21 §3）。
    session.commit()
    session.refresh(user)
    return user


def bump_token_version(session: Session, user_id: int) -> int:
    """把版本 +1 并返回新值（BE-028），调用方负责 commit。

    必须用 `FOR UPDATE`（当前读）：MySQL RR 隔离级别下，本事务在 `login()` /
    `get_current_user()` 里已经建立了一致性快照，普通 SELECT 会读回**旧版本**，
    于是签出去的 token 版本落后、下一次请求立刻 401；SQLite 会忽略该子句（本来就有写锁）。

    现在只有"全踢"动作（改密、未来的管理员强制下线）调用它——登录/登出都不能 +1。
    """
    current = session.scalar(
        select(User.token_version).where(User.id == user_id).with_for_update()
    )
    new = (current or 0) + 1
    session.execute(update(User).where(User.id == user_id).values(token_version=new))
    return new


def change_password(
    session: Session, user: User, current_password: str, new_password: str
) -> None:
    """改密（BE-029）：验旧密码 → 写新散列 → 版本 +1 让所有设备重新登录。"""
    key = f"user:{user.id}"
    change_password_limiter.check("change-password", key)

    if not verify_password(current_password, user.password_hash):
        change_password_limiter.record("change-password", key)
        raise ApiError(ErrorCode.AUTH_INVALID_CREDENTIALS, "当前密码不正确", 401)
    if current_password == new_password:
        raise ApiError(ErrorCode.VALIDATION_ERROR, "新密码不能与当前密码相同", 400)

    user.password_hash = hash_password(new_password)
    # BE-030：改密成功即解除强制改密；临时密码过期时间一并清掉，
    # 否则门禁已放开但登录还会拿旧的 24h 期限做判断。
    user.must_change_password = False
    user.temp_password_expires_at = None
    user.token_version = bump_token_version(session, user.id)
    session.commit()
    change_password_limiter.reset("change-password", key)
