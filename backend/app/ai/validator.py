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

# LaTeX 分隔符必须成对；05 §7.3 只允许 $...$ / $$...$$，\(\) 视为不合规
_INLINE_MATH = re.compile(r"\\[\(\)]")


def _normalize_for_compare(text: str) -> str:
    """去掉空白与常见标点后再比，避免「只是排版不同」被当成同一道题。"""
    return re.sub(r"[\s，。；：、（）(){}\[\]$\\*_-]", "", text.lower())


def similarity(a: str, b: str) -> float:
    """归一化后的相似度 0–1（05 §7.2 第 3 条的判据）。"""
    return SequenceMatcher(None, _normalize_for_compare(a), _normalize_for_compare(b)).ratio()


class AnalysisResult(BaseModel):
    """05 §6.4 analysis JSON 的形状，BE-006 落库前用它校验。"""

    topic_type: str = Field(min_length=1)
    difficulty: Difficulty
    knowledge_points: list[str] = Field(min_length=1, max_length=8)
    error_reasons: list[str] = Field(max_length=8)
    solution_summary: str = Field(min_length=1)

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

    @field_validator("content_md")
    @classmethod
    def content_is_self_contained_text(cls, value: str) -> str:
        """05 §7.2：不依赖图片、LaTeX 分隔符成对（题干是作答对象，答案/解析里提图无妨）。"""
        if _IMAGE_DEPENDENCY.search(value):
            raise ValueError("生成题不能依赖图片（出现「如图/图中/下图」等说法）")
        if value.count("$") % 2:
            raise ValueError("题干里的 `$` 不成对，LaTeX 公式没闭合")
        if _INLINE_MATH.search(value):
            raise ValueError("公式统一用 `$...$`，不要用 `\\(...\\)`")
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
) -> list[GeneratedQuestionSpec]:
    """05 §7.2 的六道校验：恰好 N 题、非空（由 schema 的 min_length 保证）、
    不与原题高度重复（归一化相似度 <0.9）、三题彼此不重复、不依赖图片、LaTeX 成对、长度限制。

    `original_content_md` 由 worker 用 partial 注入；不传就跳过与原题的比对
    （单测里直接喂 JSON 时不必构造原题）。
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
        raise ValueError('输出必须是 {"questions": [...]}')
    questions = raw["questions"]
    if len(questions) != expected_count:
        raise ValueError(f"应生成 {expected_count} 道题，实际 {len(questions)} 道")
    specs = [GeneratedQuestionSpec.model_validate(item) for item in questions]

    seen: list[str] = []
    for index, spec in enumerate(specs, start=1):
        for previous in seen:
            if similarity(spec.content_md, previous) >= 0.9:
                raise ValueError(f"第 {index} 题与前面生成的题目高度重复")
        seen.append(spec.content_md)
        if original_content_md and similarity(spec.content_md, original_content_md) >= 0.9:
            raise ValueError(f"第 {index} 题与原题高度重复，换个数值或情境重出")
    return specs
