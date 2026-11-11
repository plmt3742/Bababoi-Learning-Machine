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
    ValidationError,
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

# 05 §5.2：错题题干 ≤5000 字符；生成题题干 ≤3000（在 ai/validator 里管）
CONTENT_MD_MAX = 5000

MasterStatus = Literal["unmastered", "reviewing", "mastered"]

# ADR-006：三段并发的难度档。三段的默认递增档（easy/medium/hard）写在
# services/task_service，这里只管"接口能收哪些值"。
SegmentDifficulty = Literal["easy", "medium", "hard"]


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


def structure_problem_zh(question_type: str, exc: ValidationError) -> str:
    """把 `validate_type_payload` 的报错变成一句中文。

    判据不在这里重复——只翻译文案。Pydantic 对数组长度给的是默认英文
    （"List should have at least 2 items after validation, not 1"），原样透给用户
    等于让他在题目卡片或错误提示里读一句英文；我们自己 raise 的那些本来就是中文，直接带走。

    放在这里而不是 `ai/validator.py`，是因为识图降级和 PATCH 复核**都要用**这句话：
    翻译逻辑跟着判据走才不会再分叉。
    """
    error = (exc.errors() or [{}])[0]
    context = error.get("ctx") or {}
    field_label = {"choice": "选项", "blank": "空位答案"}.get(question_type, "结构")
    if error.get("type") == "too_short":
        return f"{field_label}只有 {context.get('actual_length', '?')} 个（至少要 {context.get('min_length', '?')} 个）"
    if error.get("type") == "too_long":
        return f"{field_label}有 {context.get('actual_length', '?')} 个（最多 {context.get('max_length', '?')} 个）"
    # 我们自己在 validator 里 raise 的 ValueError 会被 Pydantic 冠一句 "Value error, "，
    # 那是框架的包装不是内容
    message = str(error.get("msg") or "").removeprefix("Value error, ").strip()
    return message or "结构不完整"


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
    content_md: str = Field(max_length=CONTENT_MD_MAX)
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
    """PATCH /questions/{id}；05 §6.4 允许改：题干/答案/解析/学科/章节/标签/analysis/掌握状态
    + **题型结构三字段 `question_type`/`options`/`blanks`**（issue #43 / BE-025）。

    题型结构原来明确写"不在可改清单里——改题型等于换一道题，MVP 不支持"。
    这条被 FE-027 的完整三题型编辑器推翻了：前端已经能编辑选项/空位并 PATCH 上来，
    后端不收就等于**用户改的结构静默丢失**（前端只能事后比对再提示"后端尚未支持"）。
    判据不新写一份：改完仍由 `validate_type_payload` 整题复核，规则只有一处。

    mastery_status 也在可改清单里：前端自评后顺手 PATCH（确认单 B-5 定的口径），
    后端不做「答对 N 次自动升 reviewing」的流转，那属于 P1。
    """

    subject: str | None = Field(default=None, min_length=1, max_length=32)
    chapter: str | None = Field(default=None, max_length=64)
    content_md: str | None = Field(default=None, max_length=CONTENT_MD_MAX)
    answer_md: str | None = None
    explanation_md: str | None = None
    mastery_status: MasterStatus | None = None
    tags: list[str] | None = Field(default=None, max_length=10)
    analysis: dict | None = None
    question_type: Literal["choice", "blank", "solve"] | None = None
    options: list[ChoiceOption] | None = None
    blanks: list[BlankAnswer] | None = None

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
    question_id: int
    stage: str
    status: str
    target_index: int | None
    difficulty: SegmentDifficulty | None  # ADR-006：这一段的难度档；analysis 任务为 None
    retry_index: int
    error_code: str | None
    error_message: str | None  # 任务中心要显示「为什么失败」，只有 code 前端得硬背码表
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class TaskListOut(BaseModel):
    """GET /tasks 的信封（此前返回裸 dict，OpenAPI 只能写成 additionalProperties）。"""

    items: list[TaskOut]


class TaskIdOut(BaseModel):
    """POST /questions/{id}/analyze：只回一个入队任务 id。"""

    task_id: int


class GeneratedTaskRef(BaseModel):
    """POST /questions/{id}/generate 的 `tasks[]` 元素（ADR-006）。"""

    task_id: int
    target_index: int | None
    difficulty: SegmentDifficulty | None


class GenerateTasksOut(BaseModel):
    tasks: list[GeneratedTaskRef]


class GenerateRequest(BaseModel):
    """生题入队参数（14 号 D1/Q4）。

    - 整组：不给 `target_index`，可给 3 个 `difficulties`；不给就按默认递增档
    - 单段：给 `target_index`（1–3），可给单个 `difficulty`；不给按那一格的默认档
    两个难度字段混用是给不出：整组只给 `difficulty` 会变成"三格同一个档"，
    而 UI 上的自定义难度（P1）也应该是 3 个值，所以宁可直接拒掉。
    """

    target_index: int | None = Field(default=None, ge=1, le=3)
    difficulty: SegmentDifficulty | None = None
    difficulties: list[SegmentDifficulty] | None = None

    @model_validator(mode="after")
    def shape_matches_scope(self) -> GenerateRequest:
        if self.target_index is None:
            if self.difficulty is not None:
                raise ValueError("整组生成请用 difficulties；difficulty 只在指定 target_index 时给")
            if self.difficulties is not None and len(self.difficulties) != 3:
                raise ValueError(f"difficulties 需要 3 个难度档，实际 {len(self.difficulties)} 个")
        elif self.difficulties is not None:
            raise ValueError("单段生成请用 difficulty；difficulties 只在整组时给")
        return self


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
    # 错题本要显示原图/缩略图只能靠这一项：详情里有、列表里没有的话，
    # 前端要么逐条再请求一次详情，要么干脆不显示（实测就是这么丢的）
    image_path: str | None
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
            image_path=question.image_path,
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


class GeneratedQuestionOut(BaseModel):
    """一道 AI 相似题（05 §5.2 generated_questions，US-4 的展示字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_question_id: int
    content_md: str
    answer_md: str
    explanation_md: str
    question_type: str | None
    options: list | None
    blanks: list | None
    difficulty: str | None
    # ADR-006：①②③ 的格位。前端三张卡按它对齐，NULL 是迁移前的老数据
    target_index: int | None
    model: str | None
    prompt_version: str | None
    validation_status: str
    created_at: datetime


class QuestionDetail(QuestionOut):
    """详情 = 题目全量 + 任务列表（+ 可选的生成题列表）。

    tasks 有默认值：ORM 的 Question 上没有 tasks 关系，路由里查出来再填。
    """

    tasks: list[TaskOut] = []
    generated_questions: list[GeneratedQuestionOut] = []
