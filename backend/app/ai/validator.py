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
    structure_problem_zh,
    validate_type_payload,
)

Difficulty = Literal["easy", "medium", "hard"]

# 报错文案里要说人话：给用户看 "choice" 不如给"选择题"（BE-026 的题型不一致提示用）
TYPE_ZH = {"choice": "选择题", "blank": "填空题", "solve": "解答题"}

# 05 §5.2：生成题题干 ≤3000（比错题的 5000 更严，AI 长篇输出本身就是要拦的信号）
GENERATED_CONTENT_MD_MAX = 3000

# 05 §7.2 第 4 条：生成题不能依赖图片
_IMAGE_DEPENDENCY = re.compile(r"如[图中下上]|见下?图|照图")
# 顶层说明里能定位到具体某一条的那句。实测四张真图 4/4 都写成「第5题题干被截断」
# 「第1条仅能辨认到公式」这种开头——定位得到就下沉到条目，因为前端的确认步骤
# 只看条目的 incomplete（17 号 §四-4），写在顶层就等于用户看不见。
_TOP_ITEM_POINTER = re.compile(r"^第\s*(\d+)\s*(?:条|题|小问|个)")


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
    """一道从图里认出来的题目条目（前端 `ExtractedImageQuestion` 的对端）。

    `subject`/`chapter`/`difficulty` 是**初判**：只有图上有依据时才填（页眉的「习题 7.1」
    这类标题只有图片看得见，analysis 读文本永远读不到），前端拿去做预填与展示，
    正式难度仍以 analysis 为准。三个都可空——判断不了就留空，不许编。
    """

    index: int = 1
    content_md: str = Field(min_length=1, max_length=EXTRACTED_CONTENT_MD_MAX)
    question_type: Literal["choice", "blank", "solve"] = "solve"
    subject: str | None = None
    chapter: str | None = None
    difficulty: Difficulty | None = None
    options: list[ExtractedOption] | None = None
    blanks: list[ExtractedBlank] | None = None
    has_figure: bool = False
    warnings: list[str] = Field(default_factory=list)
    incomplete: bool = False

    @field_validator("content_md", mode="before")
    @classmethod
    def math_normalized(cls, value: str) -> str:
        return normalize_math_delimiters(value) if isinstance(value, str) else value

    @field_validator("subject", "chapter", mode="before")
    @classmethod
    def blank_text_is_none(cls, value: object) -> object:
        """空串/纯空白统一成 None，别让前端拿到 '' 再判一次真假。"""
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None if value is None else value

    @field_validator("difficulty", mode="before")
    @classmethod
    def unknown_difficulty_becomes_none(cls, value: object) -> object:
        """初判难度写错档（比如 "中等"/"mid"）时留空，不因此丢掉整条题目。

        这三个字段是锦上添花，任何一个是坏值都不该让一道认出来的题消失——
        和"提取比入库宽"是同一条原则。
        """
        if isinstance(value, str) and value.strip() in {"easy", "medium", "hard"}:
            return value.strip()
        return None


def validate_extraction(raw: dict) -> dict:
    """识图输出的校验：**文字转录从严，题目结构从宽**（ADR-004「识别成文本」的落地口径）。

    分成两类处理，是因为它们对用户的代价不一样：

    1. **题干本身残缺**（漏字、`[不清]`、图被截断）→ 条目照样返回，标 `incomplete` +
       warning。用户能看到"这一题只认出一半"，编辑两下就能用。
    2. **结构不自洽**（选择题只 1 个选项、填空题空位数≠答案数、答案为空）→
       **降级成纯文本条目**（`question_type=solve`、`options/blanks` 清空）+ warning。
       契约里 `options?`/`blanks?` 是可选（ADR-004 §5），识图不该对用户假装自己结构化成功了；
       实测密页 4 条里有 2 条是"图上 2 个空只读出 1 个答案"，原样返回的话用户要在
       **提交那一步**才被 `POST /questions` 的严格校验拒掉，而且拒的原因他看不见。
       结构化交还给 FE-020 的三题型编辑器，那里用户改得动。

    **判据只有一条是硬的：条目带任何 `warnings` 就置 `incomplete=true`**——前端的确认步骤
    看的是标志位而不是文案（17 号 §四-4），残缺只写在 warnings 里等于没告诉用户要核对。

    单条坏输出（连对象都不是）只丢那一条 + 顶层 warning，不拖垮整张图；
    图里没题返回 `questions=[]` + warning，**这不是错误**。
    LaTeX 定界符统一规范化（实测 `json_object` 模式下模型更爱吐 `\\(...\\)`），
    排版习惯不算失败。
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
        # 结构自不自洽，只问一个地方：`schemas/question.py::validate_type_payload`
        # 是题型规则的唯一来源，识图这边不再自己抄一份判据。
        structure_problem = None
        if item.question_type == "solve":
            if item.options or item.blanks:
                structure_problem = "识别为解答题却读出了选项/空位"
            item.options = item.blanks = None
        else:
            payload_options = [o.model_dump() for o in (item.options or [])]
            payload_blanks = [b.model_dump() for b in (item.blanks or [])]
            try:
                validate_type_payload(item.question_type, item.content_md,
                                      payload_options, payload_blanks)
            except ValidationError as exc:
                structure_problem = structure_problem_zh(item.question_type, exc)
        if structure_problem:
            # 不自洽就**降级成纯文本条目**，而不是把半套结构原样交给用户：
            # ADR-004 §5 里 `options?`/`blanks?` 本来就是可选，识图的职责是"识别成文本"，
            # 结构化归 FE-020 编辑器。实拍密页有 2/4 条是"图上 2 个空只读出 1 个答案"，
            # 原样返回的话用户要在"提交"那一步才被严格校验拒掉——那才是体验事故。
            # ADR-004 §6 的复审条件（结构化成功率 <90%）就是这件事的预案入口。
            item.incomplete = True
            item.question_type = "solve"
            item.options = item.blanks = None
            item.warnings.append(
                f"{structure_problem}，已按文本题返回；需要选择题/填空题请在编辑器里补结构"
            )
        if item.warnings:
            # 残缺必须落到 `incomplete` 上，不能只留在 `warnings` 里：17 号 §四-4 让前端
            # 「`incomplete=true` 的条目要用户补完才能提交」，那条确认步骤读的是标志位，
            # 不是文案。实测四张真图（11-07）：模型把"被截断/辨认不清"写进 warnings，
            # 却不打 `[不清]` 标记，于是半截题干带着 `incomplete=false` 进了前端。
            item.incomplete = True
        items.append(item)

    # 顶层那句只要点得到第几条，就搬到那一条上去（顺带把 incomplete 顶起来）。
    # 实测模型常把"第 5 题被截断"写在顶层而不是条目的 warnings 里，留在顶层就变成
    # 横幅上有、卡片上没有——用户照样会直接提交半截题干。
    # 按 item.index（= 模型自己的编号）查而不是按列表下标：坏输出被丢掉之后列表会前移，
    # 用列表下标会把"第 1 条题干为空，已跳过"挂到幸存下来的那道题上（测试里真复现过）。
    by_index = {item.index: item for item in items}
    kept: list[str] = []
    for text in top_warnings:
        match = _TOP_ITEM_POINTER.match(text.strip())
        target = by_index.get(int(match.group(1))) if match else None
        if target is not None:
            target.warnings.append(text)
            target.incomplete = True
        else:
            kept.append(text)
    top_warnings = kept

    if not items and not top_warnings:
        top_warnings.append("没有从图片里辨认出题目")
    return {"questions": items, "warnings": top_warnings}


def validate_segment(
    raw: dict,
    *,
    difficulty: str | None = None,
    original_content_md: str | None = None,
    sibling_content_mds: tuple[str, ...] = (),
    original_question_type: str | None = None,
    type_policy: str = "soft",
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
    if (
        type_policy == "strict"
        and original_question_type
        and spec.question_type != original_question_type
    ):
        # BE-026（issue #44）：开关开启时题型必须与原题一致。抛 ValueError 而不是新增
        # TYPE_MISMATCH 错误码——pipeline 会把它归成"坏输出"，于是任务级那一次重试
        # 自动生效，终态仍是 AI_INVALID_OUTPUT（你们 §8 要求不新增同义错误码）。
        raise ValueError(
            f"这一段是{TYPE_ZH.get(spec.question_type, spec.question_type)}，"
            f"原题是{TYPE_ZH.get(original_question_type, original_question_type)}；"
            "当前设置要求与原题同题型，请在个人设置里关闭该开关或按原题题型重出"
        )
    return spec
