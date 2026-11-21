"""限流引擎：统一走 `limits` 的 MovingWindow（精确滑动窗口），存储可换。

为什么是 MovingWindow 而不是固定窗口：固定窗口在边界处会突刺——限 10/分钟，
00:00:45 打满 10 次、00:01:45 再打满 10 次，两秒内放行 20 次。登录、注册这类
安全端点不能接受；滑动窗口把"任意 60 秒内最多 N 次"真正守住。

存储：
- 默认 `memory://`：进程内，只对单实例成立（和之前的实现同档，但过期清理与锁由
  limits 负责，业务侧不再维护 deque）。
- 多实例时把 `RATE_LIMIT_STORAGE_URL` 换成 `redis://host:6379/0`（需要安装
  `limits[redis]`），业务代码与调用点都不用改。
"""
from __future__ import annotations

from limits import RateLimitItem, parse, strategies
from limits.storage import Storage, storage_from_string

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode


def build_storage(url: str | None = None) -> Storage:
    return storage_from_string(url or settings.rate_limit_storage_url)


def validate_rate_limit_config() -> None:
    """启动期把限流配置解析一遍：写错在启动时就炸，别等第一个请求。

    与 `settings.validate_for_startup()` 同一风格；解析规则和运行时共用
    `limits.parse`，不另写一份。
    """
    for rate in (
        f"{settings.login_rate_limit}/{settings.login_rate_window_s} seconds",
        f"{settings.register_rate_limit}/{settings.register_rate_window_s} seconds",
    ):
        parse(rate)


class SlidingWindowLimiter:
    """按 key 计数的滑动窗口（精确到每次提交的时间戳）。

    三个动作分开，调用方按语义选：
    - `hit()`  记账，超限抛 429（AI 提交这类"超过就不能做"的端点）
    - `check()` 只看不记账，超限抛 429（登录这类"先查，失败才记账"的端点）
    - `record()` 只记账、不抛（登录失败路径）
    """

    def __init__(
        self,
        rate: str,
        *,
        code: ErrorCode,
        message: str,
        storage: Storage | None = None,
    ) -> None:
        # parse 放在构造期：模块加载/启动时就校验配置，不在第一个请求里才发现写错
        self.item: RateLimitItem = parse(rate)
        self.code = code
        self.message = message
        self._storage = storage or build_storage()
        self._limiter = strategies.MovingWindowRateLimiter(self._storage)

    def hit(self, *identifiers: str) -> None:
        if not self._limiter.hit(self.item, *identifiers):
            raise ApiError(self.code, self.message, 429)

    def record(self, *identifiers: str) -> None:
        """记一次；超限由 `check()` 负责报错，这里不抛。"""
        self._limiter.hit(self.item, *identifiers)

    def check(self, *identifiers: str) -> None:
        if not self._limiter.test(self.item, *identifiers):
            raise ApiError(self.code, self.message, 429)

    def reset(self, *identifiers: str) -> None:
        self._limiter.clear(self.item, *identifiers)

    def clear(self) -> None:
        """清空全部计数；**只给测试复位用**。

        红线：生产别调。memory:// 下每个 limiter 有独立存储，互不影响；
        换成 redis:// 后 `reset()` 是 flushdb，会清掉同一个 DB 里的所有键
        （包括其他限流桶），不是只清自己这一类。
        """
        self._storage.reset()
