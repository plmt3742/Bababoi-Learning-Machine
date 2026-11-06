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
# 既稳又不雷同。
# quiz 的 max_tokens：一段只出 1 道，但实测单段输出到过 3589 / 3450 token
# （含参 solve 带小问 + 长解析），4000 只剩 10% 余量。max_tokens 是上限不是配额，
# 按实际输出计费，所以给 6000 换"不被截断成解析失败"，不额外花钱。
SAMPLING = {
    OPERATION_ANALYSIS: {"temperature": 0.2, "max_tokens": 4000},
    OPERATION_QUIZ: {"temperature": 0.3, "max_tokens": 6000},
    # 识图：05 §7.0 定温度 0.1。max_tokens 8000 是实测给的——同一张 4 题图
    # 开 response_format=json_object 是 7.7s / 1513 token，不开会跑偏到 44.1s / 7265 token
    # 并几乎顶到上限，所以留够头寸，别让截断把整页题变成坏输出。
    OPERATION_VISION: {"temperature": 0.1, "max_tokens": 8000},
}


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    # "length" 意味着输出被 max_tokens 掐断，JSON 必然不完整。
    # 不带上它，截断只能以"解析失败"的形式冒出来，排查时要猜是模型笨还是上限小了。
    finish_reason: str | None = None


class LLMClient(Protocol):
    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        """发一次对话；网络/超时/供应商错误抛 AIError 子类。"""
        ...


class MockLLMClient:
    """settings.llm_mock=True 时使用。输出按 operation 从 _MOCK_OUTPUTS 取。

    quiz 是单段出题（ADR-006），Mock 也从提示词里读难度档来选输出——否则三段
    拿到同一份 mock 题，"按格替换""与同组查重"这些逻辑在 mock 模式下永远跑不到。
    """

    def complete(self, operation: str, messages: list[dict]) -> LLMResponse:
        if operation == OPERATION_QUIZ:
            text = _mock_quiz_text(messages)
        elif operation == OPERATION_VISION:
            text = _MOCK_OUTPUTS[OPERATION_VISION]
        else:
            text = _MOCK_OUTPUTS[operation]
        return LLMResponse(
            text=text,
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
            finish_reason="stop",
        )


def _mock_quiz_text(messages: list[dict]) -> str:
    user = messages[-1]["content"] if messages else ""
    difficulty = next((d for d in ("easy", "medium", "hard") if f"难度档：{d}" in user), "medium")
    return json.dumps(_MOCK_QUIZ_SEGMENTS[difficulty], ensure_ascii=False)


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
        extra: dict = {}
        if operation == OPERATION_VISION:
            # 抄题不需要思考；开着的时候思考 token 会顶满 max_tokens，
            # 表现成"输出被截断"而不是"模型不会"（05 §6.8 实测表）
            extra["thinking"] = {"type": "enabled" if settings.vision_thinking else "disabled"}
        try:
            resp = self._client.with_options(timeout=_timeout_for(operation)).chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},  # 实测 deepseek-flash 支持（与图片同用也可）
                **sampling,
                extra_body=extra or None,
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
            finish_reason=resp.choices[0].finish_reason,
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

# 一段一题：三个难度档各给一份合法输出（必须能过 ai/validator 的单段校验）。
_MOCK_QUIZ_SEGMENTS: dict[str, dict] = {
    "easy": {
        "question_type": "blank",
        "content_md": "曲线 $y=2x^3-6x$ 在 $x=1$ 处的切线斜率为 ___。",
        "answer_md": "$0$",
        "explanation_md": "求导得 $y'=6x^2-6$，代入 $x=1$ 即得斜率 $0$。",
        "blanks": [{"index": 1, "answer_md": "$0$"}],
        "difficulty": "easy",
    },
    "medium": {
        "question_type": "solve",
        "content_md": "求函数 $g(x)=x^3-3x$ 的单调区间与极值。",
        "answer_md": "增区间 $(-\\infty,-1)$ 与 $(1,+\\infty)$，减区间 $(-1,1)$；极大值 $2$，极小值 $-2$。",
        "explanation_md": "求导得 $g'(x)=3x^2-3$，解 $g'(x)>0$ 与 $g'(x)<0$ 即得单调区间与极值。",
        "difficulty": "medium",
    },
    "hard": {
        "question_type": "choice",
        "content_md": "若函数 $p(x)=x^3-3a x$ 在 $x=2$ 处取得极小值，则实数 $a$ 的值为（  ）。",
        "answer_md": "选 A",
        "explanation_md": "$p'(x)=3x^2-3a$，由 $p'(2)=0$ 得 $a=4$；两侧符号由负变正，确为极小值。",
        "options": [
            {"label": "A", "content_md": "$a=4$"},
            {"label": "B", "content_md": "$a=2$"},
        ],
        "difficulty": "hard",
    },
}

# 识图的固定输出：故意三种"残缺"各来一条，让宽松提取校验的分支在 CI 里真被跑到
# （空答案的填空、只读出一个选项的选择、依赖图形的题）。
_MOCK_VISION: dict = {
    "questions": [
        {
            "index": 1,
            "content_md": "求函数 $f(x)=x^3-3x^2+2$ 的极值。",
            "question_type": "solve",
            "has_figure": False,
            "warnings": [],
        },
        {
            "index": 2,
            "content_md": "设 $A=\\begin{pmatrix}2&1\\\\1&2\\end{pmatrix}$，则 $A$ 的特征值为 ___ 和 ___。",
            "question_type": "blank",
            "blanks": [{"index": 1, "answer_md": "$3$"}],
            "has_figure": False,
            "warnings": [],
        },
        {
            "index": 3,
            "content_md": "如图，在三角形 $ABC$ 中，$CD$ 是 $AB$ 边上的高，$AC=4$，$BC=3$，求 $CD$。",
            "question_type": "solve",
            "has_figure": True,
            "warnings": ["含图，暂只提取文字"],
        },
    ],
    "warnings": [],
}

_MOCK_OUTPUTS: dict[str, str] = {
    OPERATION_ANALYSIS: json.dumps(_MOCK_ANALYSIS, ensure_ascii=False),
    OPERATION_VISION: json.dumps(_MOCK_VISION, ensure_ascii=False),
}
