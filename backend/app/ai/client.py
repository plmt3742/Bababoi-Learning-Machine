"""LLM 客户端：协议 + DeepSeek 实现 + Mock 实现 + 工厂。

- DeepSeek 走 OpenAI 兼容接口（ADR-003），官方 SDK 换 base_url 即可
- Mock 不发网络请求，返回固定合法输出，CI 与本地默认用它（12号 §6.1）
- complete 返回 LLMResponse：文本 + token 用量 + 耗时，供 ai_call_logs 落库
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Protocol

import httpx
import openai

from app.ai.errors import AIProviderError, AITimeoutError
from app.ai.llm_config import LLMConfig, system_config
from app.core.config import settings

# 操作类型：决定 mock 返回哪种输出、日志里记什么 operation
OPERATION_ANALYSIS = "analysis"
OPERATION_QUIZ = "quiz"

# 05 §8：识图是同步等待（90s）；分析/生题在队列里跑（单任务硬超时 120s）。
# 之前统一用 90s，等于把后台任务也按同步请求掐——这里按操作分档。
OPERATION_VISION = "vision"

# BE-024 两跳的提示词标记：Mock 靠它区分第 1/2 跳（真实客户端不看这两个常量）。
VISION_STEP_TEXT = "步骤：逐题转录"
VISION_STEP_STRUCTURE = "步骤：结构化拆题"


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
    def complete(
        self,
        operation: str,
        messages: list[dict],
        *,
        max_tokens: int | None = None,
        thinking: str | None = None,
    ) -> LLMResponse:
        """发一次对话；网络/超时/供应商错误抛 AIError 子类。

        `max_tokens` / `thinking` 按调用覆盖：识图两跳的思考档位与输出上限不同
        （转录 adaptive + 16000、结构化 disabled + 8000），放在 operation 档位上不够用。
        """
        ...


class MockLLMClient:
    """settings.llm_mock=True 时使用。输出按 operation 从 _MOCK_OUTPUTS 取。

    quiz 是单段出题（ADR-006），Mock 从提示词里读**难度档和原题题型**来选输出：
    - 按难度分卡，否则三段拿到同一份 mock 题，"按格替换""与同组查重"这些逻辑
      在 mock 模式下永远跑不到；
    - 按题型分卡，否则 strict（默认开启）下原题是选择题/填空题时三格全会被判死——
      mock 是替身，不该逼着演示和测试去关业务开关。
    """

    key_source = "mock"

    def complete(
        self,
        operation: str,
        messages: list[dict],
        *,
        max_tokens: int | None = None,
        thinking: str | None = None,
    ) -> LLMResponse:
        if operation == OPERATION_QUIZ:
            text = _mock_quiz_text(messages)
        elif operation == OPERATION_VISION:
            text = _mock_vision_text(messages)
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


def _mock_vision_text(messages: list[dict]) -> str:
    """识图两跳各给一份固定输出；靠提示词里的步骤标记区分。"""
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    if VISION_STEP_TEXT in system:
        return json.dumps(_MOCK_VISION_TEXT, ensure_ascii=False)
    return json.dumps(_MOCK_VISION_STRUCTURE, ensure_ascii=False)


# 提示词里「- 题型：选择题」这句是 Mock 选卡的依据（prompts.quiz_messages 固定格式）。
# client.py 不能 import prompts（prompts 反过来 import 这里的 OPERATION_*），码表抄一份。
_MOCK_TYPE_BY_CN = {"选择题": "choice", "填空题": "blank", "解答题": "solve"}


def _mock_quiz_text(messages: list[dict]) -> str:
    user = messages[-1]["content"] if messages else ""
    difficulty = next((d for d in ("easy", "medium", "hard") if f"难度档：{d}" in user), "medium")
    question_type = next(
        (code for label, code in _MOCK_TYPE_BY_CN.items() if f"题型：{label}" in user),
        "solve",  # 提示词里读不到题型时退回解答题（生成题默认题型）
    )
    return json.dumps(_MOCK_QUIZ_SEGMENTS[(question_type, difficulty)], ensure_ascii=False)


class DeepSeekClient:
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        # trust_env=False：不让 httpx 去读系统代理。Windows/macOS 上代理一坏，
        # 请求会变成 APIConnectionError: SSL UNEXPECTED_EOF，看着像模型挂了
        # 其实是网络配置问题（本地实测踩过一次，排查成本很高）。
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            # 兜底值；真正生效的是每次请求按 operation 覆盖的 timeout
            timeout=settings.task_hard_timeout_s,
            max_retries=settings.task_retry_limit,  # SDK 自带传输层重试
            http_client=httpx.Client(
                trust_env=False, timeout=settings.task_hard_timeout_s
            ),
        )
        self._model = model
        self.key_source = "system"
        self.user_id: int | None = None

    def complete(
        self,
        operation: str,
        messages: list[dict],
        *,
        max_tokens: int | None = None,
        thinking: str | None = None,
    ) -> LLMResponse:
        start = time.monotonic()
        sampling = dict(SAMPLING.get(operation, {}))
        if max_tokens is not None:
            sampling["max_tokens"] = max_tokens
        extra: dict = {}
        if operation == OPERATION_VISION:
            # BE-024：两跳各自指定档位（转录 adaptive、结构化 disabled）；
            # 没指定时默认关思考（抄题不需要推理，思考 token 会顶满上限变成截断）
            extra["thinking"] = {"type": thinking or "disabled"}
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


_client_cache: dict[tuple[str, str, str], DeepSeekClient] = {}
_client_cache_lock = threading.Lock()


def build_llm_client(config: LLMConfig | None = None) -> LLMClient:
    """按配置返回客户端；同一把 Key（哈希）+ base_url + model 复用一个连接池。

    缓存键用 Key 哈希而不是 user_id：用户换 Key 后自然落到新键，旧客户端不会再被取到，
    不需要额外的失效回调。
    """
    if settings.llm_mock:
        return MockLLMClient()
    cfg = config or system_config()
    if not cfg.api_key:
        raise AIProviderError("LLM_MOCK=false 但 API Key 未配置")
    handle = hashlib.sha256(cfg.api_key.encode()).hexdigest()[:12]
    cache_key = (handle, cfg.base_url, cfg.model)
    with _client_cache_lock:
        client = _client_cache.get(cache_key)
        if client is None:
            client = DeepSeekClient(
                api_key=cfg.api_key, base_url=cfg.base_url, model=cfg.model
            )
            client.key_source = cfg.key_source
            client.user_id = cfg.user_id
            _client_cache[cache_key] = client
        return client


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

# 一段一题：题型 × 难度各给一份合法输出（必须能过 ai/validator 的单段校验）。
# 每题型 3 份而不是 1 份：三段默认 easy/medium/hard，同题型三段若回同一张卡，
# 会撞 §7.2 第 3 条的「与同组其它段完全相同」判死。九张卡互相不同，也不与原题样例相同。
# 注意：难度字段只是卡自己的标注，worker 会按请求档位覆盖（validator.validate_segment）。
_MOCK_QUIZ_SEGMENTS: dict[tuple[str, str], dict] = {
    ("blank", "easy"): {
        "question_type": "blank",
        "content_md": "曲线 $y=2x^3-6x$ 在 $x=1$ 处的切线斜率为 ___。",
        "answer_md": "$0$",
        "explanation_md": "求导得 $y'=6x^2-6$，代入 $x=1$ 即得斜率 $0$。",
        "blanks": [{"index": 1, "answer_md": "$0$"}],
        "difficulty": "easy",
    },
    ("blank", "medium"): {
        "question_type": "blank",
        "content_md": "函数 $y=x^3-3x$ 的极大值为 ___，极小值为 ___。",
        "answer_md": "极大值 $2$，极小值 $-2$。",
        "explanation_md": "求导得 $y'=3x^2-3$，驻点为 $x=\\pm 1$；$x=-1$ 处取极大值 $2$，"
                          "$x=1$ 处取极小值 $-2$。",
        "blanks": [{"index": 1, "answer_md": "$2$"}, {"index": 2, "answer_md": "$-2$"}],
        "difficulty": "medium",
    },
    ("blank", "hard"): {
        "question_type": "blank",
        "content_md": "若函数 $y=x^3-3ax$ 在 $x=2$ 处取得极小值，则实数 $a=$ ___。",
        "answer_md": "$4$",
        "explanation_md": "$y'=3x^2-3a$，由 $y'(2)=0$ 得 $a=4$；此时 $y''(2)>0$，确为极小值。",
        "blanks": [{"index": 1, "answer_md": "$4$"}],
        "difficulty": "hard",
    },
    ("choice", "easy"): {
        "question_type": "choice",
        "content_md": "下列函数中，在 $x=0$ 处取得极小值的是（  ）。",
        "answer_md": "选 A",
        "explanation_md": "$y=x^2$ 在 $x=0$ 处取最小值 $0$；$y=-x^2$ 在 $x=0$ 处取极大值。",
        "options": [
            {"label": "A", "content_md": "$y=x^2$"},
            {"label": "B", "content_md": "$y=-x^2$"},
        ],
        "difficulty": "easy",
    },
    ("choice", "medium"): {
        "question_type": "choice",
        "content_md": "函数 $y=x^3-3x$ 的极大值为（  ）。",
        "answer_md": "选 A",
        "explanation_md": "求导得 $y'=3x^2-3$，$x=-1$ 处导数由正变负，故极大值为 $y(-1)=2$。",
        "options": [
            {"label": "A", "content_md": "$2$"},
            {"label": "B", "content_md": "$-2$"},
            {"label": "C", "content_md": "$0$"},
            {"label": "D", "content_md": "$1$"},
        ],
        "difficulty": "medium",
    },
    ("choice", "hard"): {
        "question_type": "choice",
        "content_md": "若函数 $p(x)=x^3-3a x$ 在 $x=2$ 处取得极小值，则实数 $a$ 的值为（  ）。",
        "answer_md": "选 A",
        "explanation_md": "$p'(x)=3x^2-3a$，由 $p'(2)=0$ 得 $a=4$；两侧符号由负变正，确为极小值。",
        "options": [
            {"label": "A", "content_md": "$a=4$"},
            {"label": "B", "content_md": "$a=2$"},
            {"label": "C", "content_md": "$a=-4$"},
            {"label": "D", "content_md": "$a=-2$"},
        ],
        "difficulty": "hard",
    },
    ("solve", "easy"): {
        "question_type": "solve",
        "content_md": "求函数 $h(x)=x^2-4x+1$ 的最小值，并写出取得最小值时 $x$ 的值。",
        "answer_md": "最小值 $-3$，此时 $x=2$。",
        "explanation_md": "配方得 $h(x)=(x-2)^2-3$，二次函数开口向上，顶点处取最小值。",
        "difficulty": "easy",
    },
    ("solve", "medium"): {
        "question_type": "solve",
        "content_md": "求函数 $g(x)=x^3-3x$ 的单调区间与极值。",
        "answer_md": "增区间 $(-\\infty,-1)$ 与 $(1,+\\infty)$，减区间 $(-1,1)$；极大值 $2$，极小值 $-2$。",
        "explanation_md": "求导得 $g'(x)=3x^2-3$，解 $g'(x)>0$ 与 $g'(x)<0$ 即得单调区间与极值。",
        "difficulty": "medium",
    },
    ("solve", "hard"): {
        "question_type": "solve",
        "content_md": "设函数 $f(x)=x^3-3ax$ 在 $x=1$ 处取得极值，求实数 $a$ 的值，"
                      "并判断该极值是极大值还是极小值。",
        "answer_md": "$a=1$；$x=1$ 处为极小值。",
        "explanation_md": "由 $f'(1)=0$ 得 $a=1$；$f'(x)=3(x-1)(x+1)$，在 $x=1$ 两侧由负变正，"
                          "故为极小值。",
        "difficulty": "hard",
    },
}

# 第 2 跳（结构化）的固定输出：把提取校验的四条分支各来一条——
# 结构自洽的填空（保留 blank）、结构不自洽的填空（降级成文本）、依赖图形的题、
# 初判坏值（非法档位 → None）。这些分支只有 mock 能钉死，实拍图每次不一样。
_MOCK_VISION_TEXT: dict = {
    "chapter": "复习题六",
    "questions": [
        {"index": 1, "content_md": "求函数 $f(x)=x^3-3x^2+2$ 的极值。"},
        {
            "index": 2,
            "content_md": "设 $A=\\begin{pmatrix}2&1\\\\1&2\\end{pmatrix}$，"
            "则 $A$ 的特征值为 \\underline{\\qquad} 和 \\underline{\\qquad}。",
        },
        {
            "index": 3,
            "content_md": "极限 $\\lim_{x\\to 0}\\dfrac{\\sin 3x}{x}= $ ___，"
            "$\\lim_{x\\to\\infty}\\dfrac{1}{x}= $ ___。",
        },
        {
            "index": 4,
            "content_md": "如图，在三角形 $ABC$ 中，$CD$ 是 $AB$ 边上的高，"
            "$AC=4$，$BC=3$，求 $CD$。",
        },
    ],
    "warnings": [],
}

_MOCK_VISION_STRUCTURE: dict = {
    "questions": [
        {
            "index": 1,
            "content_md": "求函数 $f(x)=x^3-3x^2+2$ 的极值。",
            "question_type": "solve",
            "subject": "高等数学",
            "chapter": "习题 7.1",
            "difficulty": "medium",
            "has_figure": False,
            "warnings": [],
        },
        {
            "index": 2,
            "content_md": "设 $A=\\begin{pmatrix}2&1\\\\1&2\\end{pmatrix}$，则 $A$ 的特征值为 ___ 和 ___。",
            "question_type": "blank",
            # 学科由请求参数写死覆盖（17 号对齐清单 §三 规则 1），这里给一个"错"的值好验它
            "subject": "线性代数",
            "chapter": "复习题六",
            # 故意给一个非法档位：初判坏值不该让整条题目消失（validator 会降级成 None）
            "difficulty": "中等",
            "blanks": [{"index": 1, "answer_md": "$3$"}, {"index": 2, "answer_md": "$1$"}],
            "has_figure": False,
            "warnings": [],
        },
        {
            # 实拍密页 4 条里就有 2 条是这种"图上 2 个空只读出 1 个答案"：
            # 结构不自洽 → 识图不假装成功，降级成纯文本条目，结构化交还给编辑器
            "index": 3,
            "content_md": "极限 $\\lim_{x\\to 0}\\dfrac{\\sin 3x}{x}= $ ___，$\\lim_{x\\to\\infty}\\dfrac{1}{x}= $ ___。",
            "question_type": "blank",
            "blanks": [{"index": 1, "answer_md": "$3$"}],
            "has_figure": False,
            "warnings": [],
        },
        {
            "index": 4,
            "content_md": "如图，在三角形 $ABC$ 中，$CD$ 是 $AB$ 边上的高，$AC=4$，$BC=3$，求 $CD$。",
            "question_type": "solve",
            # 三项都拿不准时给 null，前端要能接受"没有初判"这条路径
            "subject": None,
            "chapter": None,
            "difficulty": None,
            "has_figure": True,
            "warnings": ["含图，暂只提取文字"],
        },
    ],
    "warnings": [],
}

_MOCK_OUTPUTS: dict[str, str] = {
    OPERATION_ANALYSIS: json.dumps(_MOCK_ANALYSIS, ensure_ascii=False),
    OPERATION_VISION: json.dumps(_MOCK_VISION_STRUCTURE, ensure_ascii=False),
}
