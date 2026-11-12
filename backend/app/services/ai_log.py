"""AI 调用日志的统一写入口（05 §9.3）。

之前这段只在 task_worker 里有一份。识图是同步调用、不经过队列，但它同样要留
token/延迟/坏输出原文，否则成本统计和排查只覆盖队列那半边。
规则只维护一份：独立短事务、写失败不拖垮主流程、原文截到 8000 字。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import sessionmaker

from app.ai.client import LLMResponse
from app.ai.prompts import prompt_version
from app.core.config import settings
from app.models import AiCallLog

logger = logging.getLogger(__name__)

RAW_TEXT_LIMIT = 8000


def write_call_log(
    session_factory: sessionmaker,
    user_id: int,
    operation: str,
    status: str,
    question_id: int | None = None,
    usage: LLMResponse | None = None,
    error_code: str | None = None,
    raw_text: str | None = None,
    queue_wait_ms: int | None = None,
    type_policy: str | None = None,
) -> None:
    """日志写不进去也不能把业务带崩，所以这里吞掉一切异常，只留一条 error 日志。"""
    try:
        with session_factory() as session:
            session.add(
                AiCallLog(
                    user_id=user_id,
                    question_id=question_id,
                    operation=operation,
                    model=usage.model if usage else settings.llm_model,
                    prompt_version=prompt_version(operation, type_policy=type_policy),
                    type_policy=type_policy,
                    input_tokens=usage.prompt_tokens if usage else None,
                    output_tokens=usage.completion_tokens if usage else None,
                    latency_ms=usage.latency_ms if usage else 0,
                    queue_wait_ms=queue_wait_ms,
                    status=status,
                    error_code=error_code,
                    raw_response=(raw_text or "")[:RAW_TEXT_LIMIT],
                )
            )
            session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("ai_call_logs 写入失败（user=%s, operation=%s）", user_id, operation)
