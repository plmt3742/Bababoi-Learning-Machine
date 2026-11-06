"""AI 输出的 Pydantic 校验：分析结果与生成题。

生成题的题型规则不在重复写——GeneratedQuestionSpec 复用 schemas/question.py 的
validate_type_payload，和人工录入走同一套规则（选项字母顺序、空位数=答案数）。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.question import (
    MAX_BLANKS,
    MAX_OPTIONS,
    MIN_OPTIONS,
    BlankAnswer,
    ChoiceOption,
    validate_type_payload,
)

Difficulty = Literal["easy", "medium", "hard"]

# 05 §5.2：生成题题干 ≤3000（比错题的 5000 更严，AI 长篇输出本身就是要拦的信号）
GENERATED_CONTENT_MD_MAX = 3000

# 05 §7.2 第 4 条：生成题不能依赖图片
_IMAGE_DEPENDENCY = re.compile(r"如[图中下上]|见下?图|照图")


def _normalize_for_compare(text: str) -> str:
    """去掉空白与常见标点后再比，避免「只是排版不同」被当成同一道题。"""
    return re.sub(r"[\s，。；：、（）(){}\[\]$\\*_-]", "", text.lower())


def similarity(a: str, b: str) -> float:
    """归一化后的相似度 0–1（05 §7.2 第 3 条的判据）。"""
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


def validate_quiz(
    raw: dict,
    expected_count: int = 3,
    original_content_md: str | None = None,
    original_question_type: str | None = None,
) -> list[GeneratedQuestionSpec]:
    """05 §7.2 的七道校验：恰好 N 题、非空（由 schema 的 min_length 保证）、
    题型与原题一致、不与原题高度重复（归一化相似度 <0.9）、不依赖图片、
    LaTeX 成对、长度限制。

    `original_content_md` / `original_question_type` 由 worker 用 partial 注入；
    不传就跳过与原题的比对。

    三题彼此只拒「归一化后完全相同」，**不套用 0.9**——这条是我一开始自己加的，
    真模型 4 轮实测：含参解答题三题彼此相似度 0.846–0.966（模板一样、只有函数式不同），
    按 0.9 拦会把连续两轮合法输出判死、任务直接 failed；
    而与原题的相似度最高才 0.833，说明 05 那个 0.9 阈值本来就是冲着「抄原题」设计的。
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
        raise ValueError('输出必须是 {"questions": [...]}')
    questions = raw["questions"]
    if len(questions) != expected_count:
        raise ValueError(f"应生成 {expected_count} 道题，实际 {len(questions)} 道")
    specs = [GeneratedQuestionSpec.model_validate(item) for item in questions]

    if original_question_type is not None:
        mismatched = [
            index
            for index, spec in enumerate(specs, start=1)
            if spec.question_type != original_question_type
        ]
        if mismatched:
            raise ValueError(
                "生成题题型必须与原题一致"
                f"（原题 {original_question_type}，第 {mismatched[0]} 题为 "
                f"{specs[mismatched[0] - 1].question_type}）"
            )

    seen: list[str] = []
    for index, spec in enumerate(specs, start=1):
        normalized = _normalize_for_compare(spec.content_md)
        if normalized in seen:
            raise ValueError(f"第 {index} 题与前面生成的题目完全相同")
        seen.append(normalized)
        if original_content_md and similarity(spec.content_md, original_content_md) >= 0.9:
            raise ValueError(f"第 {index} 题与原题高度重复，换个数值或情境重出")
    return specs
