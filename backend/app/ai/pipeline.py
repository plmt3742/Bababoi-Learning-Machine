"""LLM 调用编排：一次操作 = 调模型 → 提取 JSON → 校验，失败重试一次。

12号 §3.2 的重试规则在这里实现（retry 1 次）；重试仍失败抛 AIInvalidOutputError，
由 service 层把任务置 failed 并写 ai_call_logs。
不持有数据库事务（05 §9.3）——本模块不 import 任何 db 代码。
"""
from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from app.ai import parser
from app.ai.client import LLMClient, LLMResponse
from app.ai.errors import AIInvalidOutputError


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
) -> PipelineResult:
    """parse 传 Pydantic 模型类，或 custom_validate 传函数（raw -> 校验后的值）。

    两者必给其一；校验失败（含 JSON 提取失败）算一次坏输出，整体重跑 retry_limit 次。
    """
    if (parse is None) == (custom_validate is None):
        raise ValueError("parse 与 custom_validate 必须二选一")

    last_error: Exception | None = None
    for attempt in range(1, retry_limit + 2):
        usage = client.complete(operation, messages)
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
    raise AIInvalidOutputError(f"重试 {retry_limit} 次后输出仍不合法：{detail}")
