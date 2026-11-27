"""管理端展示格式（28 号文档 §7 / admin/API_CONTRACT.md）。

前端 types.ts 把时间、耗时、token 数都当**展示字符串**消费（"11-27 22:41:08"、
"30.0s"、"1.2k"），所以格式化放后端，避免 10k 行前端逐页改。数据库仍一律存
UTC naive，这里只在出口换成 UTC+8。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

DISPLAY_TZ = timezone(timedelta(hours=8))


def to_display(dt: datetime | None, *, seconds: bool = True) -> str | None:
    """UTC naive → `MM-DD HH:MM[:SS]`（UTC+8）。None 原样返回。"""
    if dt is None:
        return None
    local = dt.replace(tzinfo=UTC).astimezone(DISPLAY_TZ)
    return local.strftime("%m-%d %H:%M:%S" if seconds else "%m-%d %H:%M")


def display_day(dt: datetime) -> str:
    """趋势图横轴标签 `MM-DD`（UTC+8）。"""
    return dt.replace(tzinfo=UTC).astimezone(DISPLAY_TZ).strftime("%m-%d")


def local_day_start_utc(now: datetime | None = None) -> datetime:
    """UTC+8 当天 00:00 对应的 UTC naive 时刻（"今日"统计口径）。"""
    now = now or datetime.now(UTC).replace(tzinfo=None)
    local = now.replace(tzinfo=UTC).astimezone(DISPLAY_TZ)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(UTC).replace(tzinfo=None)


def fmt_latency(latency_ms: int | None) -> str:
    if latency_ms is None:
        return "—"
    return f"{latency_ms / 1000:.1f}s"


def fmt_duration_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f} 秒"
    return f"{seconds / 60:.1f} 分钟"


def fmt_tokens(input_tokens: int | None, output_tokens: int | None) -> str:
    total = (input_tokens or 0) + (output_tokens or 0)
    if input_tokens is None and output_tokens is None:
        return "—"
    if total >= 1000:
        return f"{total / 1000:.1f}k"
    return str(total)


def fmt_task_duration(
    *, status: str, created_at: datetime, started_at: datetime | None,
    finished_at: datetime | None, now: datetime,
) -> str:
    """任务列表的 duration 列（仅展示用）：生成中 / 等待 N 秒 / 已取消。"""
    if status == "queued":
        return f"等待 {int((now - created_at).total_seconds())} 秒"
    if status == "running":
        return "生成中"
    if status == "canceled":
        return "已取消"
    if finished_at is None or started_at is None:
        # 没有开始时间就算不出真实耗时；不拿 created_at 硬凑（失败快照里会得到负值）
        return "—"
    seconds = max((finished_at - started_at).total_seconds(), 0)
    return fmt_duration_seconds(seconds)
