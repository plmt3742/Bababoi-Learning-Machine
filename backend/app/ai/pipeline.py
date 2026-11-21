"""LLM 调用编排：一次操作 = 调模型 → 提取 JSON → 校验，失败重试一次。

12号 §3.2 的重试规则在这里实现（retry 1 次）；重试仍失败抛 AIInvalidOutputError，
由 service 层把任务置 failed 并写 ai_call_logs。
不持有数据库事务（05 §9.3）——本模块不 import 任何 db 代码。
"""
from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from app.ai import parser
from app.ai.client import LLMClient, LLMResponse
from app.ai.errors import AIInvalidOutputError, AITimeoutError, AITruncatedError


class PipelineResult:
    """校验通过的结果 + 调用元数据（写 ai_call_logs 用）。"""

    def __init__(self, value: object, usage: LLMResponse, attempts: int) -> None:
        self.value = value
        self.usage = usage
        self.attempts = attempts


def run[T: BaseModel](
    client: LLMClient,
    operation: str,
    messages: list[dict],
    parse: type[T] | None = None,
    custom_validate: Callable[[object], object] | None = None,
    retry_limit: int = 1,
    *,
    max_tokens: int | None = None,
    thinking: str | None = None,
    deadline: float | None = None,
    call_timeout_s: float | None = None,
) -> PipelineResult:
    """parse 传 Pydantic 模型类，或 custom_validate 传函数（raw -> 校验后的值）。

    两者必给其一；校验失败（含 JSON 提取失败）算一次坏输出，整体重跑 retry_limit 次。
    """
    if (parse is None) == (custom_validate is None):
        raise ValueError("parse 与 custom_validate 必须二选一")

    last_error: Exception | None = None
    last_raw: str | None = None
    for attempt in range(1, retry_limit + 2):
        timeout_s = _attempt_timeout(deadline, call_timeout_s)
        usage = client.complete(
            operation, messages, max_tokens=max_tokens, thinking=thinking, timeout_s=timeout_s
        )
        last_raw = usage.text  # 坏输出也要把原文带出去，否则没法定位 prompt
        if usage.finish_reason == "length":
            # 被 max_tokens 掐断的输出必然不是完整 JSON。这里直接抛、不再重试：
            # 同一段提示词再跑一次只会顶到同一个上限，白等一倍时间。
            raise AITruncatedError(
                f"模型输出被 max_tokens 截断（已输出 {usage.completion_tokens} token），"
                "请减少一次处理的内容量后重试",
                raw_text=usage.text,
            )
        try:
            raw = parser.extract_json(usage.text)
            value: object
            if parse is not None:
                value = parse.model_validate(raw)
            else:
                value = custom_validate(raw)
            return PipelineResult(value=value, usage=usage, attempts=attempt)
        except (AIInvalidOutputError, ValidationError, ValueError) as exc:
            last_error = exc

    detail = last_error.errors()[0]["msg"] if isinstance(last_error, ValidationError) else str(last_error)
    raise AIInvalidOutputError(f"生成结果未通过校验：{detail}", raw_text=last_raw)


def _attempt_timeout(deadline: float | None, call_timeout_s: float | None) -> float | None:
    """本次调用可用的超时：整单 deadline 剩下的时间与单次上限取小。

    deadline 用 `time.monotonic()`；剩余不足 5 秒就不再发起调用——Python 杀不掉
    阻塞在 socket 上的线程，只能靠"不再发起"把整单耗时卡住。
    """
    if deadline is None:
        return call_timeout_s
    remaining = deadline - time.monotonic()
    if remaining <= 5:
        raise AITimeoutError("识图超时，请重试")
    if call_timeout_s is None:
        return remaining - 5
    return min(call_timeout_s, remaining - 5)
