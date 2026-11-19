"""AI 提交限流（BE-016 / 05 §6.2 的 429 `AI_RATE_LIMITED`）。

只限三类会触发模型调用的提交：建题（自动入队 analysis）、显式分析/生题入队、
识图（同步调用，17–90s，单次最贵）。上传图片不算——它不碰模型。

**按用户计，不按 IP**：staging 在 nginx 后面且 `TRUSTED_PROXIES` 为空（见 05 §9.5），
按 socket 对端算会让全站共用一个桶，一个人跑满就卡住所有人；而演示账号本来就是
多人共用，按 IP 还会把观众和演示者算成同一个。按用户代价是换号可绕过（注册即可），
但 token 消耗另有 worker 并发上限（`TASK_MAX_CONCURRENCY`）兜底，这层挡的是连点/脚本。
"""
from __future__ import annotations

import threading
from collections import deque
from time import monotonic

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode


class SlidingWindowLimiter:
    """同一 key 在 `window_s` 内最多放行 `limit` 次；超出抛 429。

    记账在锁内一次完成（先判后记），并发请求不会同时挤过最后一名额。
    过期的 key 在每次记账时顺带清掉，不依赖定时器（低频事件，全表扫的代价可接受）。
    """

    def __init__(self, limit: int, window_s: int, message: str) -> None:
        self.limit = limit
        self.window_s = window_s
        self.message = message
        self._hits: dict[int, deque[float]] = {}
        # 同步端点跑在线程池里（05 §9.2），dict 读写要加锁
        self._lock = threading.Lock()

    def _prune(self, hits: deque[float], now: float) -> None:
        while hits and now - hits[0] > self.window_s:
            hits.popleft()

    def _drop_stale(self, now: float) -> None:
        for key in [k for k, d in self._hits.items() if not d or now - d[-1] > self.window_s]:
            self._hits.pop(key, None)

    def hit(self, user_id: int) -> None:
        with self._lock:
            now = monotonic()
            self._drop_stale(now)
            hits = self._hits.setdefault(user_id, deque())
            self._prune(hits, now)
            if len(hits) >= self.limit:
                raise ApiError(ErrorCode.AI_RATE_LIMITED, self.message, 429)
            hits.append(now)

    def clear(self) -> None:
        """清空全部计数；测试复位用。"""
        with self._lock:
            self._hits.clear()


# 两个桶分开计：识图一次 17–90s 且单次最贵，额度要比"入队"小一个量级。
vision_limiter = SlidingWindowLimiter(
    settings.ai_vision_rate_limit,
    settings.ai_rate_window_s,
    "识图过于频繁，请稍后再试",
)
enqueue_limiter = SlidingWindowLimiter(
    settings.ai_enqueue_rate_limit,
    settings.ai_rate_window_s,
    "AI 任务提交过于频繁，请稍后再试",
)
