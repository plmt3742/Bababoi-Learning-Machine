"""题型结构与入库前置校验。

依据 05 §5.2 的字段形状（`options = [{label, content_md}]`、`blanks = [{index, answer_md}]`）
与 PRD 5.2.2 / 5.2.4 的规则。这两节在 PRD v0.7、v0.8、撤回版里一字未动。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

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


# ---- API 层（BE-004，05 §6.4）：请求/响应形状 ----

# 05 只说「列表不返回全文，返回 excerpt」，没定长度；取 100 字符，超出加省略号
EXCERPT_LEN = 100

MasterStatus = Literal["unmastered", "reviewing", "mastered"]


def validate_type_payload(
    question_type: str, content_md: str, options: list | None, blanks: list | None
) -> None:
    """按题型分发到 ChoiceQuestion/BlankQuestion 的校验器。

    题型规则只在这里维护一份：API 创建（BE-004）和 PATCH 后的整题复核都走这里。
    不合法抛 pydantic 的 ValidationError，由调用方决定转成什么错误。
    """
    payload: dict = {"question_type": question_type, "content_md": content_md}
    if question_type == "choice":
        payload["options"] = options or []
    elif question_type == "blank":
        payload["blanks"] = blanks or []
    TypeAdapter(QuestionInput).validate_python(payload)


def clean_tag_names(value: list[str]) -> list[str]:
    """去首尾空白、拒空名；tags.name 列宽是 64。"""
    names = []
    for raw in value:
        name = raw.strip()
        if not name:
            raise ValueError("标签名不能为空")
        if len(name) > 64:
            raise ValueError("标签名最长 64 字符")
        names.append(name)
    return names


def make_excerpt(content_md: str) -> str:
    """压掉换行和连续空白后截断；列表页只展示这一段，不回传全文。"""
    compact = " ".join(content_md.split())
    if len(compact) <= EXCERPT_LEN:
        return compact
    return compact[:EXCERPT_LEN] + "…"


class QuestionCreate(QuestionBase):
    """POST /questions 的请求体；字段名与 05 §6.4 的表格一致（扁平结构）。

    题型规则（选项字母顺序、空位数=答案数）不在重复写，
    通过 validate_type_payload 复用上面三个题型类的校验器。
    """

    subject: str = Field(min_length=1, max_length=32)
    chapter: str | None = Field(default=None, max_length=64)
    source_type: Literal["text", "image"] = "text"
    question_type: Literal["choice", "blank", "solve"]
    answer_md: str | None = None
    explanation_md: str | None = None
    options: list[ChoiceOption] | None = None
    blanks: list[BlankAnswer] | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)
    image_path: str | None = Field(default=None, max_length=255)

    @field_validator("tags")
    @classmethod
    def tag_names_are_clean(cls, value: list[str]) -> list[str]:
        return clean_tag_names(value)

    @model_validator(mode="after")
    def matches_type_rules(self) -> QuestionCreate:
        validate_type_payload(self.question_type, self.content_md, self.options, self.blanks)
        return self


class QuestionUpdate(BaseModel):
    """PATCH /questions/{id}；05 §6.4 允许改：题干/答案/解析/学科/标签/analysis。

    options/blanks 不在可改清单里——改题型等于换一道题，MVP 不支持。
    """

    subject: str | None = Field(default=None, min_length=1, max_length=32)
    chapter: str | None = Field(default=None, max_length=64)
    content_md: str | None = None
    answer_md: str | None = None
    explanation_md: str | None = None
    tags: list[str] | None = Field(default=None, max_length=10)
    analysis: dict | None = None

    @field_validator("tags")
    @classmethod
    def tag_names_are_clean(cls, value: list[str] | None) -> list[str] | None:
        return clean_tag_names(value) if value is not None else None

    @field_validator("content_md")
    @classmethod
    def content_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("题干不能为空")
        return value


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str


class TaskOut(BaseModel):
    """任务中心/详情页要展示的字段（05 §3.1 generation_task）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    status: str
    target_index: int | None
    retry_index: int
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class QuestionOut(BaseModel):
    """完整题目（05 §6.4 的 Question JSON 示例）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    chapter: str | None
    source_type: str
    content_md: str
    answer_md: str | None
    explanation_md: str | None
    question_type: str
    options: list | None
    blanks: list | None
    analysis: dict | None
    mastery_status: str
    tags: list[TagOut]
    image_path: str | None
    crop_box: list | None
    created_at: datetime
    updated_at: datetime


class QuestionListItem(BaseModel):
    """列表项：不给全文，只给 excerpt（05 §5.3/§6.4）。"""

    id: int
    subject: str
    chapter: str | None
    question_type: str
    excerpt: str
    mastery_status: str
    tags: list[TagOut]
    created_at: datetime

    @classmethod
    def from_question(cls, question) -> QuestionListItem:
        return cls(
            id=question.id,
            subject=question.subject,
            chapter=question.chapter,
            question_type=question.question_type,
            excerpt=make_excerpt(question.content_md),
            mastery_status=question.mastery_status,
            tags=[TagOut.model_validate(t) for t in question.tags],
            created_at=question.created_at,
        )


class QuestionPage(BaseModel):
    """分页信封（05 §6.1：items/total/page/page_size）。"""

    items: list[QuestionListItem]
    total: int
    page: int
    page_size: int


class QuestionCreateOut(BaseModel):
    """POST /questions 的返回：题目 + 已入队的 analysis 任务 id（05 §6.4）。"""

    question: QuestionOut
    task_id: int


class QuestionDetail(QuestionOut):
    """详情 = 题目全量 + 任务列表（+ 可选的生成题列表）。

    tasks 有默认值：ORM 的 Question 上没有 tasks 关系，路由里查出来再填。
    """

    tasks: list[TaskOut] = []
    generated_questions: list = []
