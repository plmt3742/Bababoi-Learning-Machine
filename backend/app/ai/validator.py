"""AI 输出的 Pydantic 校验：分析结果与生成题。

生成题的题型规则不在重复写——GeneratedQuestionSpec 复用 schemas/question.py 的
validate_type_payload，和人工录入走同一套规则（选项字母顺序、空位数=答案数）。
"""
from __future__ import annotations

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
    content_md: str = Field(min_length=1)
    answer_md: str = Field(min_length=1)
    explanation_md: str = Field(min_length=1)
    difficulty: Difficulty
    options: list[ChoiceOption] | None = None
    blanks: list[BlankAnswer] | None = None

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


def validate_quiz(raw: dict, expected_count: int = 3) -> list[GeneratedQuestionSpec]:
    """生成题恰好 expected_count 道（05：恰好 3 题，全有或全无）。"""
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
        raise ValueError('输出必须是 {"questions": [...]}')
    questions = raw["questions"]
    if len(questions) != expected_count:
        raise ValueError(f"应生成 {expected_count} 道题，实际 {len(questions)} 道")
    return [GeneratedQuestionSpec.model_validate(item) for item in questions]
