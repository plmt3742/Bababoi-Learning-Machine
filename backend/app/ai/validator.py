"""AI 输出的 Pydantic 校验：分析结果与生成题。

生成题的题型规则不在重复写——GeneratedQuestionSpec 复用 schemas/question.py 的
validate_type_payload，和人工录入走同一套规则（选项字母顺序、空位数=答案数）。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.schemas.question import (
    MAX_BLANKS,
    MAX_OPTIONS,
    MIN_OPTIONS,
    BlankAnswer,
    ChoiceOption,
    count_blanks,
    validate_type_payload,
)

Difficulty = Literal["easy", "medium", "hard"]

# 05 §5.2：生成题题干 ≤3000（比错题的 5000 更严，AI 长篇输出本身就是要拦的信号）
GENERATED_CONTENT_MD_MAX = 3000

# 05 §7.2 第 4 条：生成题不能依赖图片
_IMAGE_DEPENDENCY = re.compile(r"如[图中下上]|见下?图|照图")


def _normalize_for_compare(text: str) -> str:
    """去掉空白、全角/半角标点、LaTeX 定界符与排版宏后再比。

    这条归一化就是「逐字相同」判据的全部强度：判据唯一的价值是拦真抄题，
    而抄题最容易躲的方式就是换排版（多敲空格、`（`→`(`、`\\left(`→`(`、加 `\\\\,`）。
    所以排版层差异一律先抹平，再判是否同一句（前端意见单 §二）。
    没覆盖的：`\\ln x` vs `\\log_e x` 这类语义等价写法——那需要公式解析，
    归 P1「同组公式结构去重」，不在这里假装做到了。
    """
    for macro in ("\\left", "\\right", "\\displaystyle"):
        text = text.replace(macro, "")
    # \dfrac/\tfrac 换成 \frac：只剥样式前缀，别把 frac 这个词一起吃掉
    for macro in ("\\dfrac", "\\tfrac"):
        text = text.replace(macro, "\\frac")
    return re.sub(r"[\s，。；：、,;（）(){}\[\]$\\*_-]", "", text.lower())


def similarity(a: str, b: str) -> float:
    """归一化后的相似度 0–1。

    现在**不是**入库判据（0.9 那条在单段模式下被实测否证，见 `validate_segment`），
    留着是因为 `backend/scripts/measure_segment_similarity.py` 靠它复现那组数据，
    前端可以自己跑、不用信我的转述。删掉它等于把证据链一起删了。
    """
    return SequenceMatcher(None, _normalize_for_compare(a), _normalize_for_compare(b)).ratio()


# 05 §7.3 只允许 $...$ / $$...$$。但真模型确实会写 \(...\)（实测 6 次里 1 次），
# 那是排版习惯不是内容错误——判失败等于把一道好题扔掉，所以先规范化再校验。
_MATH_DELIMITERS = (
    (re.compile(r"\\\["), "$$"),
    (re.compile(r"\\\]"), "$$"),
    (re.compile(r"\\\("), "$"),
    (re.compile(r"\\\)"), "$"),
)


def normalize_math_delimiters(text: str) -> str:
    """`\\(...\\)` / `\\[...\\]` → `$...$` / `$$...$$`，前端 KaTeX 才认。"""
    for pattern, replacement in _MATH_DELIMITERS:
        text = pattern.sub(replacement, text)
    return text


class AnalysisResult(BaseModel):
    """05 §7.1 analysis JSON 的形状，BE-006 落库前用它校验。

    `answer_md`/`explanation_md` 也在里面：05 v0.4 明确「原题未填时由分析任务补全」，
    但落库写的是 `questions.answer_md` / `questions.explanation_md` 两个正字段，
    不塞进 analysis JSON（确认单 14 号 §3）。
    """

    topic_type: str = Field(min_length=1)
    difficulty: Difficulty
    knowledge_points: list[str] = Field(min_length=1, max_length=8)
    error_reasons: list[str] = Field(max_length=8)
    answer_md: str = Field(min_length=1)
    explanation_md: str = Field(min_length=1)
    solution_summary: str = Field(min_length=1)

    @field_validator("topic_type", "answer_md", "explanation_md", "solution_summary", mode="before")
    @classmethod
    def math_normalized(cls, value: str) -> str:
        return normalize_math_delimiters(value) if isinstance(value, str) else value

    @field_validator("knowledge_points", "error_reasons")
    @classmethod
    def items_are_clean(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned and value:
            raise ValueError("数组里有内容但全是空白")
        return cleaned


class GeneratedQuestionSpec(BaseModel):
    """一道 AI 生成题；字段与 05 §5.2 generated_questions 对齐。"""

    question_type: Literal["choice", "blank", "solve"]
    content_md: str = Field(min_length=1, max_length=GENERATED_CONTENT_MD_MAX)
    answer_md: str = Field(min_length=1)
    explanation_md: str = Field(min_length=1)
    difficulty: Difficulty
    options: list[ChoiceOption] | None = None
    blanks: list[BlankAnswer] | None = None

    @field_validator("content_md", "answer_md", "explanation_md", mode="before")
    @classmethod
    def math_normalized(cls, value: str) -> str:
        return normalize_math_delimiters(value) if isinstance(value, str) else value

    @field_validator("content_md")
    @classmethod
    def content_is_self_contained_text(cls, value: str) -> str:
        """05 §7.2：不依赖图片、LaTeX 分隔符成对（题干是作答对象，答案/解析里提图无妨）。"""
        if _IMAGE_DEPENDENCY.search(value):
            raise ValueError("生成题不能依赖图片（出现「如图/图中/下图」等说法）")
        if value.count("$") % 2:
            raise ValueError("题干里的 `$` 不成对，LaTeX 公式没闭合")
        return value

    @field_validator("options")
    @classmethod
    def options_in_range(cls, value: list[ChoiceOption] | None) -> list[ChoiceOption] | None:
        if value is not None and not (MIN_OPTIONS <= len(value) <= MAX_OPTIONS):
            raise ValueError(f"选项数必须在 {MIN_OPTIONS}–{MAX_OPTIONS} 之间")
        return value

    @field_validator("blanks")
    @classmethod
    def blanks_in_range(cls, value: list[BlankAnswer] | None) -> list[BlankAnswer] | None:
        if value is not None and not (1 <= len(value) <= MAX_BLANKS):
            raise ValueError(f"空位数必须在 1–{MAX_BLANKS} 之间")
        return value

    @model_validator(mode="after")
    def matches_type_rules(self) -> GeneratedQuestionSpec:
        validate_type_payload(self.question_type, self.content_md, self.options, self.blanks)
        return self


def validate_analysis(raw: dict) -> AnalysisResult:
    return AnalysisResult.model_validate(raw)


# ---- 图片文本提取（05 §7.0 / BE-014）----

# 提取阶段题干按错题的上限走（5000），不按生成题的 3000：
# 一张整页教材里的一道解答题本来就可能写得长，卡 3000 会把真题判死。
EXTRACTED_CONTENT_MD_MAX = 5000
_UNCLEAR_MARK = "[不清]"


class ExtractedOption(BaseModel):
    """提取阶段的选项。这里**允许空文本**，严格规则留给入库那一刻。"""

    label: str = ""
    content_md: str = ""

    @field_validator("content_md", "label", mode="before")
    @classmethod
    def math_normalized(cls, value: str) -> str:
        return normalize_math_delimiters(value) if isinstance(value, str) else value


class ExtractedBlank(BaseModel):
    index: int = 1
    answer_md: str = ""

    @field_validator("answer_md", mode="before")
    @classmethod
    def math_normalized(cls, value: str) -> str:
        return normalize_math_delimiters(value) if isinstance(value, str) else value


class ExtractedQuestion(BaseModel):
    """一道从图里认出来的题目条目（前端 `ExtractedImageQuestion` 的对端）。"""

    index: int = 1
    content_md: str = Field(min_length=1, max_length=EXTRACTED_CONTENT_MD_MAX)
    question_type: Literal["choice", "blank", "solve"] = "solve"
    options: list[ExtractedOption] | None = None
    blanks: list[ExtractedBlank] | None = None
    has_figure: bool = False
    warnings: list[str] = Field(default_factory=list)
    incomplete: bool = False

    @field_validator("content_md", mode="before")
    @classmethod
    def math_normalized(cls, value: str) -> str:
        return normalize_math_delimiters(value) if isinstance(value, str) else value


def validate_extraction(raw: dict) -> dict:
    """校验识图输出，**故意比入库校验宽**。

    唯一理由是"残缺不等于坏输出"：一张 4 道题的页面里只要有一道没认全，
    用户仍然应该看到另外 3 道 + 一条可编辑的残缺条目。要是这里照搬
    `schemas/question.py::validate_type_payload`（选择题必须 ≥2 项、填空题
    空位数必须等于答案数、答案非空），整张图会被判成坏输出，用户什么也拿不到——
    那比"少一个答案"糟得多。差的部分标 `incomplete` + 写进 warnings，
    严格规则等用户确认后 POST /questions 时再跑。

    另一条实测依据：DeepSeek 在 `response_format=json_object` 下更爱吐 `\\(...\\)`
    （同一张图不开 JSON 模式给的是 `$...$`），所以这里对 LaTeX 定界符做归一化，
    不让排版习惯变成失败条件。
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
        raise ValueError("识图输出必须形如 {\"questions\": [...]}")

    top_warnings = [str(w) for w in (raw.get("warnings") or []) if str(w).strip()]
    items: list[ExtractedQuestion] = []
    for position, entry in enumerate(raw["questions"], start=1):
        try:
            item = ExtractedQuestion.model_validate(entry)
        except ValidationError as exc:
            # 单条坏输出不拖垮整张图：丢掉它，留一行说明
            top_warnings.append(f"第 {position} 条无法解析（{exc.errors()[0]['msg']}），已跳过")
            continue
        if not item.content_md.strip():
            top_warnings.append(f"第 {position} 条题干为空，已跳过")
            continue
        item.index = position  # 模型编号乱了就按阅读顺序重编，前端只认连续 ①②③
        if _UNCLEAR_MARK in item.content_md:
            item.incomplete = True
            item.warnings.append("题干含 [不清] 标记，可能有漏字或误读")
        if item.has_figure and not any("含图" in w for w in item.warnings):
            item.warnings.append("含图，暂只提取文字")
        if item.question_type == "blank":
            markers = count_blanks(item.content_md)
            answers = item.blanks or []
            if not answers:
                item.incomplete = True
                item.warnings.append("识别为填空题但没读出空位答案")
            elif markers != len(answers) or any(not a.answer_md.strip() for a in answers):
                item.incomplete = True
                item.warnings.append(f"空位 {markers} 个、答案 {len(answers)} 个，或有空答案，请核对")
        elif item.question_type == "choice":
            options = item.options or []
            if len(options) < 2:
                item.incomplete = True
                item.warnings.append(f"识别为选择题但只读出 {len(options)} 个选项，请核对")
        elif item.question_type == "solve" and not (item.options or item.blanks):
            item.options = item.blanks = None
        items.append(item)

    if not items and not top_warnings:
        top_warnings.append("没有从图片里辨认出题目")
    return {"questions": items, "warnings": top_warnings}


def validate_segment(
    raw: dict,
    *,
    difficulty: str | None = None,
    original_content_md: str | None = None,
    sibling_content_mds: tuple[str, ...] = (),
) -> GeneratedQuestionSpec:
    """校验**一段**的输出（ADR-006：一次调用只出 1 道题）。

    05 §7.2 的校验项：形状非空（schema 保证）、不依赖图片、LaTeX 成对、题干 ≤3000，
    以及"不许是抄来的"——原题和其它格用的是**同一条**判据：归一化后逐字相同才判死。

    为什么与原题也不再套 0.9（14 号 D3 原本写「与原题相似度 <0.9 保留」，这条以实测改）：
    含参单调性讨论这类题的句子是固定模板，换函数族照样贴着原题写，相似度天然卡在 0.9 上下。
    真模型 2 轮 ×3 段实测（同题 `f(x)=x-a\\ln x`）：
    - 判死 4/9 与 3/9，而被判死的输出是 `$f(x)=x^2-a\\ln x$`、`$f(x)=ax-2\\sqrt x$`、
      `$f(x)=x+\\frac{a}{x}$`、`$f(x)=x-ae^x$` —— **都是换了考查结构的新题，不是抄题**；
    - 18 段里**没有一段真的逐字抄过原题**，0.9 阈值拦到的全是正常输出；
    - 合法新题最高 0.967、真抄会更高，两个分布重叠，任何 0.9–0.97 的阈值都分不开。
    所以数值阈值在这里没有鉴别力：改成逐字相同才拒，与同组其它格的判据统一。
    「同模板换数字」现在是可接受的出题，产品若要禁止，得比"公式结构差异"而不是比字符相似度。

    `difficulty`：模型自己标的档位一律改写成这一格请求的档位。详情页三张卡的难度徽章是
    "格子"的属性，让用户点第 3 格（hard）却拿到一张标 easy 的卡，比模型标错更难解释。
    """
    if not isinstance(raw, dict):
        raise ValueError("一段输出必须是一个 JSON 对象")
    spec = GeneratedQuestionSpec.model_validate(raw)
    if difficulty is not None:
        spec.difficulty = difficulty
    normalized = _normalize_for_compare(spec.content_md)
    if normalized in {_normalize_for_compare(other) for other in sibling_content_mds}:
        raise ValueError("这一段与同组其它段完全相同，换个数值或情境重出")
    if original_content_md and normalized == _normalize_for_compare(original_content_md):
        raise ValueError("这一段与原题逐字相同，换个数值或情境重出")
    return spec
