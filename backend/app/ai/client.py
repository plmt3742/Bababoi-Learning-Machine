"""LLM 客户端：协议 + DeepSeek 实现 + Mock 实现 + 工厂。

- DeepSeek 走 OpenAI 兼容接口（ADR-003），官方 SDK 换 base_url 即可
- Mock 不发网络请求，返回固定合法输出，CI 与本地默认用它（12号 §6.1）
- complete 返回 LLMResponse：文本 + token 用量 + 耗时，供 ai_call_logs 落库
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

import openai

from app.ai.errors import AIProviderError, AITimeoutError
from app.core.config import settings

# 操作类型：决定 mock 返回哪种输出、日志里记什么 operation
OPERATION_ANALYSIS = "analysis"
OPERATION_QUIZ = "quiz"

# 05 §8：识图是同步等待（90s）；分析/生题在队列里跑（单任务硬超时 120s）。
# 之前统一用 90s，等于把后台任务也按同步请求掐——这里按操作分档。
OPERATION_VISION = "vision"


def _timeout_for(operation: str) -> int:
    if operation == OPERATION_VISION:
        return settings.recognize_client_timeout_s
    return settings.task_hard_timeout_s


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class LLMClient(Protocol):
    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        """发一次对话；网络/超时/供应商错误抛 AIError 子类。"""
        ...


class MockLLMClient:
    """settings.llm_mock=True 时使用。输出按 operation 从 _MOCK_OUTPUTS 取。"""

    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        return LLMResponse(
            text=_MOCK_OUTPUTS[operation],
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
        )


class DeepSeekClient:
    def __init__(self) -> None:
        self._client = openai.OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            # 兜底值；真正生效的是每次请求按 operation 覆盖的 timeout
            timeout=settings.task_hard_timeout_s,
            max_retries=settings.task_retry_limit,  # SDK 自带传输层重试
        )
        self._model = settings.llm_model

    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        start = time.monotonic()
        try:
            resp = self._client.with_options(timeout=_timeout_for(operation)).chat.completions.create(
                model=self._model, messages=messages
            )
        except openai.APITimeoutError as exc:
            raise AITimeoutError(str(exc)) from None
        except openai.APIError as exc:
            raise AIProviderError(str(exc)) from None

        return LLMResponse(
            text=resp.choices[0].message.content or "",
            model=resp.model,
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            latency_ms=int((time.monotonic() - start) * 1000),
        )


def build_llm_client() -> LLMClient:
    if settings.llm_mock:
        return MockLLMClient()
    if not settings.llm_api_key:
        raise AIProviderError("LLM_MOCK=false 但 LLM_API_KEY 未配置")
    return DeepSeekClient()


# ---- Mock 固定输出（合法 JSON，必须能通过 ai/validator 的校验，pipeline 测试依赖这点）----

_MOCK_ANALYSIS = {
    "topic_type": "导数与极值",
    "difficulty": "medium",
    "knowledge_points": ["导数", "极值", "单调性"],
    "error_reasons": ["求导后未判断符号变化"],
    "solution_summary": "求导，令导数为 0 求驻点，列表判断两侧符号得极值。",
}

_MOCK_QUIZ = {
    "questions": [
        {
            "question_type": "solve",
            "content_md": "按导数与极值的方法，求函数 $g(x)=x^3-3x$ 的单调区间。",
            "answer_md": "增区间 $(-\\infty,-1)\\cup(1,+\\infty)$，减区间 $(-1,1)$。",
            "explanation_md": "求导得 $g'(x)=3x^2-3$，解 $g'(x)>0$ 与 $g'(x)<0$ 即得。",
            "difficulty": "medium",
        },
        {
            "question_type": "blank",
            "content_md": "函数 $g(x)=x^3-3x$ 的极大值为 ___。",
            "answer_md": "$2$",
            "explanation_md": "驻点 $x=-1$ 处 $g(-1)=2$，两侧符号由正变负，为极大值。",
            "blanks": [{"index": 1, "answer_md": "$2$"}],
            "difficulty": "easy",
        },
        {
            "question_type": "choice",
            "content_md": "$g(x)=x^3-3x$ 的极小值点是（  ）。",
            "answer_md": "选 A",
            "explanation_md": "$g'(x)=0$ 得 $x=\\pm1$；$x=1$ 两侧先负后正，为极小值点。",
            "options": [
                {"label": "A", "content_md": "$x=1$"},
                {"label": "B", "content_md": "$x=-1$"},
            ],
            "difficulty": "easy",
        },
    ]
}

_MOCK_OUTPUTS: dict[str, str] = {
    OPERATION_ANALYSIS: json.dumps(_MOCK_ANALYSIS, ensure_ascii=False),
    OPERATION_QUIZ: json.dumps(_MOCK_QUIZ, ensure_ascii=False),
}
