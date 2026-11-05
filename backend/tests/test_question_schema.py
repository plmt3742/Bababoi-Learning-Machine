"""题型结构与入库前置校验的测试。

函数名按「行为」命名，这份文件可以直接当 05 §5.2 + PRD 5.2.2 / 5.2.4 的可执行规格读。
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.question import (
    MAX_OPTIONS,
    BlankAnswer,
    BlankQuestion,
    ChoiceQuestion,
    QuestionInput,
    SolveQuestion,
    count_blanks,
    expected_label,
)

AnyQuestion = ChoiceQuestion | BlankQuestion | SolveQuestion


def parse_question(payload: dict) -> AnyQuestion:
    """走 QuestionInput 分发，顺带验证 question_type 真的被用上了。"""

    class Wrapper(BaseModel):
        question: QuestionInput

    return Wrapper.model_validate({"question": payload}).question


def options(*texts: str) -> list[dict]:
    """按顺序生成合法选项，省掉每个测试都手写 label。"""
    return [
        {"label": expected_label(i), "content_md": text}
        for i, text in enumerate(texts, start=1)
    ]


def blanks(*texts: str) -> list[dict]:
    return [{"index": i, "answer_md": text} for i, text in enumerate(texts, start=1)]


def test_choice_with_four_options_is_valid() -> None:
    q = parse_question(
        {
            "question_type": "choice",
            "content_md": "已知 $x^2=4$，则 $x=$",
            "options": options("2", "-2", "$\\pm 2$", "4"),
        }
    )
    assert isinstance(q, ChoiceQuestion)
    assert q.multiple is False  # 单选是默认


def test_choice_accepts_lowercase_labels() -> None:
    q = parse_question(
        {
            "question_type": "choice",
            "content_md": "下列正确的是",
            "options": [
                {"label": "a", "content_md": "甲"},
                {"label": "b", "content_md": "乙"},
            ],
            "multiple": True,
        }
    )
    assert q.multiple is True


def test_choice_label_out_of_order_rejected() -> None:
    """05 把 label 存进库，所以顺序错了必须报错，不能默默接受。"""
    with pytest.raises(ValidationError, match="label 应为 B"):
        parse_question(
            {
                "question_type": "choice",
                "content_md": "题干",
                "options": [
                    {"label": "A", "content_md": "甲"},
                    {"label": "C", "content_md": "乙"},
                ],
            }
        )


def test_blank_content_md_rejected() -> None:
    with pytest.raises(ValidationError, match="题干不能为空"):
        parse_question(
            {"question_type": "choice", "content_md": "   ", "options": options("甲", "乙")}
        )


def test_one_option_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_question(
            {"question_type": "choice", "content_md": "题干", "options": options("甲")}
        )


def test_max_options_allowed_and_one_more_rejected() -> None:
    many = [expected_label(i) for i in range(1, MAX_OPTIONS + 1)]
    payload = [
        {"label": label, "content_md": f"选项{label}"} for label in many
    ]
    parse_question({"question_type": "choice", "content_md": "题干", "options": payload})
    with pytest.raises(ValidationError):
        parse_question(
            {
                "question_type": "choice",
                "content_md": "题干",
                "options": payload + [{"label": "Z", "content_md": "多余"}],
            }
        )


def test_option_with_blank_text_rejected() -> None:
    with pytest.raises(ValidationError, match="选项文本不能为空"):
        parse_question(
            {
                "question_type": "choice",
                "content_md": "题干",
                "options": options("甲", "  "),
            }
        )


def test_blank_answer_count_must_match_marker_count() -> None:
    with pytest.raises(ValidationError, match="2 个空位，答案却是 1 个"):
        parse_question(
            {"question_type": "blank", "content_md": "a=___，b=___", "blanks": blanks("1")}
        )


def test_blank_without_marker_rejected() -> None:
    with pytest.raises(ValidationError, match="没有空位标记"):
        parse_question({"question_type": "blank", "content_md": "没有下划线", "blanks": blanks("1")})


def test_blank_with_empty_answer_rejected() -> None:
    with pytest.raises(ValidationError, match="每个空位都要有答案"):
        parse_question({"question_type": "blank", "content_md": "a=___", "blanks": blanks("  ")})


def test_blank_index_must_be_sequential() -> None:
    with pytest.raises(ValidationError, match="index 应为 2"):
        parse_question(
            {
                "question_type": "blank",
                "content_md": "a=___，b=___",
                "blanks": [
                    BlankAnswer(index=1, answer_md="1"),
                    BlankAnswer(index=7, answer_md="2"),
                ],
            }
        )


def test_more_than_twenty_blanks_rejected() -> None:
    content = "，".join(["x=___"] * 21)
    with pytest.raises(ValidationError):
        parse_question(
            {"question_type": "blank", "content_md": content, "blanks": blanks(*(["1"] * 21))}
        )


def test_solve_needs_only_content_md() -> None:
    q = parse_question(
        {"question_type": "solve", "content_md": "设数列 $\\{a_n\\}$ 满足……求通项。"}
    )
    assert isinstance(q, SolveQuestion)


def test_content_md_is_not_rewritten() -> None:
    raw = "  已知 $x \\in \\mathbb{R}$，求证。  "
    q = parse_question({"question_type": "solve", "content_md": raw})
    assert q.content_md == raw  # 校验只判空白，不 trim：回给前端要能一模一样


def test_four_underscore_run_counts_as_one_blank() -> None:
    """PRD 把「>3 归一为 3」列为非 P0，所以 `____` 的口径还没定。
    当前实现按一段连续下划线算一个空位；改口径时这条测试要一起改。
    """
    assert count_blanks("a=____") == 1
    assert count_blanks("a=___ 和 b=_____ 和 c=__") == 2


def test_blank_question_exposes_structured_answers() -> None:
    q = parse_question(
        {"question_type": "blank", "content_md": "a=___", "blanks": blanks("$0$")}
    )
    assert isinstance(q, BlankQuestion)
    assert q.blanks[0].answer_md == "$0$"  # LaTeX 源码原样存
