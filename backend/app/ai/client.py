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

import httpx
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


# 采样参数按操作分档。生成温度定 0.3 而不是 05 §7.3 原先写的 0.7：
# 实测 0.3 下三段并发的三题相似度只有 0.535–0.622（0.7 的 batch 是 0.907–0.950），
# 既稳又不雷同。max_tokens 8000 是给 hard 档留的——实测含参 hard 段一次输出 7089 token，
# 卡 4000 会把 JSON 截断成解析失败。
SAMPLING = {
    OPERATION_ANALYSIS: {"temperature": 0.2, "max_tokens": 4000},
    OPERATION_QUIZ: {"temperature": 0.3, "max_tokens": 8000},
}


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
    """settings.llm_mock=True 时使用。生成题按原题题型返回对应 mock 输出。"""

    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        text = (
            _mock_quiz_output(messages)
            if operation == OPERATION_QUIZ
            else _MOCK_OUTPUTS[operation]
        )
        return LLMResponse(
            text=text,
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
        )


def _mock_quiz_output(messages: list[dict]) -> str:
    """从 user 消息里的原题取题型，返回同题型的 3 道 mock 题（题型硬约束）。"""
    question_type = "solve"
    try:
        user_content = messages[-1]["content"]
        raw_question = user_content.split("<question>", 1)[1].split("</question>", 1)[0]
        parsed = json.loads(raw_question)
        if parsed.get("question_type") in _MOCK_QUIZ_BY_TYPE:
            question_type = parsed["question_type"]
    except (IndexError, KeyError, json.JSONDecodeError):
        pass
    return json.dumps(_MOCK_QUIZ_BY_TYPE[question_type], ensure_ascii=False)


class DeepSeekClient:
    def __init__(self) -> None:
        # trust_env=False：不让 httpx 去读系统代理。Windows/macOS 上代理一坏，
        # 请求会变成 APIConnectionError: SSL UNEXPECTED_EOF，看着像模型挂了
        # 其实是网络配置问题（本地实测踩过一次，排查成本很高）。
        self._client = openai.OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            # 兜底值；真正生效的是每次请求按 operation 覆盖的 timeout
            timeout=settings.task_hard_timeout_s,
            max_retries=settings.task_retry_limit,  # SDK 自带传输层重试
            http_client=httpx.Client(
                trust_env=False, timeout=settings.task_hard_timeout_s
            ),
        )
        self._model = settings.llm_model

    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        start = time.monotonic()
        sampling = SAMPLING.get(operation, {})
        try:
            resp = self._client.with_options(timeout=_timeout_for(operation)).chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},  # 实测 deepseek-flash 支持
                **sampling,
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
    "answer_md": "极大值 $f(-1)=3$，极小值 $f(1)=-1$",
    "explanation_md": "求导得 $f'(x)=3x^2-3$，令其为 0 得驻点，两侧符号由正变负为极大值。",
    "solution_summary": "求导，令导数为 0 求驻点，列表判断两侧符号得极值。",
}

_MOCK_QUIZ_SOLVE = {
    "questions": [
        {
            "question_type": "solve",
            "content_md": "按导数与极值的方法，求函数 $g(x)=x^3-3x$ 的单调区间。",
            "answer_md": "增区间 $(-\\infty,-1)\\cup(1,+\\infty)$，减区间 $(-1,1)$。",
            "explanation_md": "求导得 $g'(x)=3x^2-3$，解 $g'(x)>0$ 与 $g'(x)<0$ 即得。",
            "difficulty": "medium",
        },
        {
            "question_type": "solve",
            "content_md": "求函数 $h(x)=2x^3-3x^2-12x$ 的极值。",
            "answer_md": "极大值 $h(-1)=7$，极小值 $h(2)=-20$。",
            "explanation_md": "求导得 $h'(x)=6x^2-6x-12=6(x+1)(x-2)$，列表判断符号。",
            "difficulty": "medium",
        },
        {
            "question_type": "solve",
            "content_md": "求函数 $p(x)=x^3-6x^2+9x$ 的极值。",
            "answer_md": "极大值 $p(1)=4$，极小值 $p(3)=0$。",
            "explanation_md": "求导得 $p'(x)=3x^2-12x+9=3(x-1)(x-3)$，列表判断符号。",
            "difficulty": "medium",
        },
    ]
}

_MOCK_QUIZ_BLANK = {
    "questions": [
        {
            "question_type": "blank",
            "content_md": "函数 $g(x)=x^3-3x$ 的极大值为 ___。",
            "answer_md": "$2$",
            "explanation_md": "驻点 $x=-1$ 处 $g(-1)=2$，两侧符号由正变负，为极大值。",
            "blanks": [{"index": 1, "answer_md": "$2$"}],
            "difficulty": "easy",
        },
        {
            "question_type": "blank",
            "content_md": "函数 $g(x)=x^3-3x$ 的极小值为 ___。",
            "answer_md": "$-2$",
            "explanation_md": "驻点 $x=1$ 处 $g(1)=-2$，两侧符号由负变正，为极小值。",
            "blanks": [{"index": 1, "answer_md": "$-2$"}],
            "difficulty": "easy",
        },
        {
            "question_type": "blank",
            "content_md": "函数 $g(x)=x^3-3x$ 的极小值点为 $x=$ ___。",
            "answer_md": "$1$",
            "explanation_md": "求导得 $g'(x)=3x^2-3$，令其为 0 得 $x=\\pm1$，判断符号变化即得。",
            "blanks": [{"index": 1, "answer_md": "$1$"}],
            "difficulty": "medium",
        },
    ]
}

_MOCK_QUIZ_CHOICE = {
    "questions": [
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
        {
            "question_type": "choice",
            "content_md": "$g(x)=x^3-3x$ 的极大值点是（  ）。",
            "answer_md": "选 B",
            "explanation_md": "$g'(x)=3x^2-3$；$x=-1$ 两侧先正后负，为极大值点。",
            "options": [
                {"label": "A", "content_md": "$x=1$"},
                {"label": "B", "content_md": "$x=-1$"},
            ],
            "difficulty": "easy",
        },
        {
            "question_type": "choice",
            "content_md": "$g(x)=x^3-3x$ 的单调递增区间是（  ）。",
            "answer_md": "选 A",
            "explanation_md": "由 $g'(x)>0$ 得 $x<-1$ 或 $x>1$，即两个递增区间。",
            "options": [
                {"label": "A", "content_md": "$(-\\infty,-1)\\cup(1,+\\infty)$"},
                {"label": "B", "content_md": "$(-1,1)$"},
                {"label": "C", "content_md": "$(0,+\\infty)$"},
            ],
            "difficulty": "medium",
        },
    ]
}

_MOCK_QUIZ_BY_TYPE: dict[str, dict] = {
    "solve": _MOCK_QUIZ_SOLVE,
    "blank": _MOCK_QUIZ_BLANK,
    "choice": _MOCK_QUIZ_CHOICE,
}

# 测试用混合题型样本（validator 的题型/结构规则覆盖三种题型）
_MOCK_QUIZ = {
    "questions": [
        _MOCK_QUIZ_SOLVE["questions"][0],
        _MOCK_QUIZ_BLANK["questions"][0],
        _MOCK_QUIZ_CHOICE["questions"][0],
    ]
}

_MOCK_OUTPUTS: dict[str, str] = {
    OPERATION_ANALYSIS: json.dumps(_MOCK_ANALYSIS, ensure_ascii=False),
}
