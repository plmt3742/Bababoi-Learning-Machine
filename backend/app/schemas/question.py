"""题型结构与入库前置校验。

依据 05 §5.2 的字段形状（`options = [{label, content_md}]`、`blanks = [{index, answer_md}]`）
与 PRD 5.2.2 / 5.2.4 的规则。这两节在 PRD v0.7、v0.8、撤回版里一字未动。
"""
from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# PRD 5.2.2 写死的契约值，不是可调参数，所以不放 config.py
MIN_OPTIONS = 2
MAX_OPTIONS = 24  # 选项字母最多到 Z
MAX_BLANKS = 20

_BLANK_RUN = re.compile(r"_{3,}")


def count_blanks(content_md: str) -> int:
    """按 PRD 5.2.2 数题干里的空位：连续三个下划线 `___` 为一个空位。"""
    return len(_BLANK_RUN.findall(content_md))


def expected_label(position: int, lower: bool = False) -> str:
    """第 position 项（从 1 起）应有的选项字母。"""
    letter = chr(ord("A") + position - 1)
    return letter.lower() if lower else letter


class QuestionBase(BaseModel):
    """三种题型共有的题干字段。"""

    content_md: str

    @field_validator("content_md")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        """题干非空（PRD 5.2.4）。只判空白，不改写——原文要能原样回给前端核对。"""
        if not value.strip():
            raise ValueError("题干不能为空")
        return value


class ChoiceOption(BaseModel):
    """单个选项。`label` 由 05 定为必填，因此这里校验它和顺序一致。"""

    label: str
    content_md: str

    @field_validator("content_md")
    @classmethod
    def option_has_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("选项文本不能为空")
        return value


class BlankAnswer(BaseModel):
    """单个空位的答案。"""

    index: int
    answer_md: str

    @field_validator("answer_md")
    @classmethod
    def answer_has_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("每个空位都要有答案")
        return value


class ChoiceQuestion(QuestionBase):
    """选择题（PRD 5.2.2）：题干 + 2–24 个有序选项。"""

    question_type: Literal["choice"]
    options: list[ChoiceOption] = Field(min_length=MIN_OPTIONS, max_length=MAX_OPTIONS)
    multiple: bool = False  # 单选是默认，多选由用户标记

    @model_validator(mode="after")
    def labels_follow_order(self) -> ChoiceQuestion:
        """label 必须等于「按顺序推导出的字母」，大小写都可。

        05 把 label 存进库里，那就必须有人保证它和数组顺序不打架——
        否则会出现「文本写 C 却排第二位」，而排序、判分、渲染各信一份。
        """
        for position, option in enumerate(self.options, start=1):
            label = option.label.strip()
            if label.upper() != expected_label(position):
                raise ValueError(
                    f"第 {position} 个选项的 label 应为 {expected_label(position)}"
                    f"（或 {expected_label(position, lower=True)}），实际是 {label!r}"
                )
        return self


class BlankQuestion(QuestionBase):
    """填空题（PRD 5.2.2）：题干里的空位数必须与答案数相等。"""

    question_type: Literal["blank"]
    blanks: list[BlankAnswer] = Field(min_length=1, max_length=MAX_BLANKS)

    @model_validator(mode="after")
    def blanks_match_markers(self) -> BlankQuestion:
        """空位数即答案数（PRD 5.2.2），且 index 从 1 连续递增。"""
        expected = count_blanks(self.content_md)
        if expected == 0:
            raise ValueError("题干中没有空位标记 ___")
        if len(self.blanks) != expected:
            raise ValueError(f"题干有 {expected} 个空位，答案却是 {len(self.blanks)} 个")
        for position, blank in enumerate(self.blanks, start=1):
            if blank.index != position:
                raise ValueError(f"第 {position} 个答案的 index 应为 {position}，实际是 {blank.index}")
        return self


class SolveQuestion(QuestionBase):
    """解答题（PRD 5.2.2）：题干是一个整体，小问靠排版编号表达。

    PRD 5.2.4 提到的「作答区」在 05 里对应 `questions.answer_md`（原题答案，可选），
    属于错题主表字段而不是题型字段，所以这里不出现。
    """

    question_type: Literal["solve"]


QuestionInput = Annotated[
    ChoiceQuestion | BlankQuestion | SolveQuestion,
    Field(discriminator="question_type"),
]
"""按 question_type 分发到对应题型。取值与 05 §5.2 一致：choice/blank/solve。"""
