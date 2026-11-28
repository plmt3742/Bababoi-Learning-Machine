"""#126 / 05 §6.5：GET /practice/due 今日待复习队列。"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.base import utcnow
from app.models import GeneratedQuestion, PracticeRecord, Question
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def user(client: TestClient) -> tuple[str, int]:
    data = register_user(client)
    return data["access_token"], data["user"]["id"]


def _question(
    db, user_id: int, *, subject: str = "高等数学", mastery: str = "unmastered", deleted=False
) -> Question:
    with db() as s:
        row = Question(
            user_id=user_id,
            subject=subject,
            content_md=f"求函数 $f(x)=x^2$ 的极值（{subject}）。",
            question_type="solve",
            mastery_status=mastery,
        )
        if deleted:
            row.deleted_at = utcnow()
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def _generated(db, user_id: int, parent_id: int, *, deleted=False) -> GeneratedQuestion:
    with db() as s:
        row = GeneratedQuestion(
            parent_question_id=parent_id,
            user_id=user_id,
            content_md="求 $g(x)=x^3$ 的极值。",
            answer_md="极大值在 $x=0$。",
            explanation_md="求导。",
            question_type="solve",
        )
        if deleted:
            row.deleted_at = utcnow()
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def _record(db, user_id: int, generated_id: int, *, correct=True, days_ago=0.0) -> PracticeRecord:
    with db() as s:
        row = PracticeRecord(
            user_id=user_id,
            generated_question_id=generated_id,
            user_answer="x",
            is_correct=correct,
            duration_seconds=30,
            created_at=utcnow() - timedelta(days=days_ago),
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def _due(client, token, **params) -> dict:
    resp = client.get("/api/v1/practice/due", params=params, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_never_practiced_first_with_shape(client, db, user) -> None:
    token, user_id = user
    never_q = _question(db, user_id, mastery="unmastered")
    never_g = _generated(db, user_id, never_q.id)

    old_q = _question(db, user_id, mastery="mastered")
    old_g = _generated(db, user_id, old_q.id)
    _record(db, user_id, old_g.id, days_ago=8)

    body = _due(client, token)

    assert body["total"] == 2
    first, second = body["items"]
    assert first["due_reason"] == "never"
    assert first["last_practiced_at"] is None
    assert first["parent"]["id"] == never_q.id
    assert first["parent"]["subject"] == "高等数学"
    assert first["parent"]["excerpt"]
    assert first["generated_question"]["id"] == never_g.id

    assert second["due_reason"] == "mastered_7d"
    # issue #105：新增时间字段带 Z
    assert second["last_practiced_at"].endswith("Z")


@pytest.mark.parametrize(
    ("mastery", "days_ago", "due"),
    [
        ("unmastered", 0.5, False),
        ("unmastered", 1.5, True),
        ("reviewing", 2, False),
        ("reviewing", 4, True),
        ("mastered", 6, False),
        ("mastered", 8, True),
    ],
)
def test_review_thresholds(client, db, user, mastery, days_ago, due) -> None:
    token, user_id = user
    question = _question(db, user_id, mastery=mastery)
    generated = _generated(db, user_id, question.id)
    _record(db, user_id, generated.id, days_ago=days_ago)

    body = _due(client, token)
    assert body["total"] == (1 if due else 0)
    if due:
        assert body["items"][0]["due_reason"] == {
            "unmastered": "unmastered_1d",
            "reviewing": "reviewing_3d",
            "mastered": "mastered_7d",
        }[mastery]


def test_filters_soft_deleted_and_empty_parents(client, db, user) -> None:
    token, user_id = user
    deleted_q = _question(db, user_id, deleted=True)
    _generated(db, user_id, deleted_q.id)

    alive_q = _question(db, user_id)
    _generated(db, user_id, alive_q.id, deleted=True)

    # 只有原题、没有生成题：不出现在队列里
    _question(db, user_id)

    body = _due(client, token)
    assert body["total"] == 0
    assert body["items"] == []


def test_subject_filter(client, db, user) -> None:
    token, user_id = user
    math_q = _question(db, user_id, subject="高等数学")
    _generated(db, user_id, math_q.id)
    physics_q = _question(db, user_id, subject="大学物理")
    _generated(db, user_id, physics_q.id)

    body = _due(client, token, subject="大学物理")
    assert body["total"] == 1
    assert body["items"][0]["parent"]["id"] == physics_q.id


def test_user_isolation(client, db, user) -> None:
    token, user_id = user
    other = register_user(client, username="别的人_02")
    other_id = other["user"]["id"]

    foreign_q = _question(db, other_id)
    foreign_g = _generated(db, other_id, foreign_q.id)
    _record(db, other_id, foreign_g.id)

    body = _due(client, token)
    assert body["total"] == 0


def test_one_generated_per_parent_prefers_recent_wrong(client, db, user) -> None:
    token, user_id = user
    question = _question(db, user_id)
    recent_wrong = _generated(db, user_id, question.id)
    clean = _generated(db, user_id, question.id)
    _record(db, user_id, recent_wrong.id, correct=False, days_ago=2)
    _record(db, user_id, clean.id, correct=True, days_ago=1.5)

    body = _due(client, token)
    assert body["total"] == 1
    assert body["items"][0]["generated_question"]["id"] == recent_wrong.id


def test_limit_clamps_and_total_is_before_limit(client, db, user) -> None:
    token, user_id = user
    for _ in range(3):
        question = _question(db, user_id)
        _generated(db, user_id, question.id)

    body = _due(client, token, limit=1)
    assert len(body["items"]) == 1
    assert body["total"] == 3

    clamped = _due(client, token, limit=100)
    assert len(clamped["items"]) == 3
    assert clamped["total"] == 3


def test_oldest_practice_sorts_after_never(client, db, user) -> None:
    token, user_id = user
    newest_q = _question(db, user_id)
    newest_g = _generated(db, user_id, newest_q.id)
    _record(db, user_id, newest_g.id, days_ago=2)

    oldest_q = _question(db, user_id)
    oldest_g = _generated(db, user_id, oldest_q.id)
    _record(db, user_id, oldest_g.id, days_ago=9)

    never_q = _question(db, user_id)
    _generated(db, user_id, never_q.id)

    body = _due(client, token)
    ids = [item["parent"]["id"] for item in body["items"]]
    assert ids == [never_q.id, oldest_q.id, newest_q.id]


def test_resegment_does_not_reset_last_practiced(client, db, user) -> None:
    """整组重生成软删旧题后，旧题上的流水仍要算「最近练习过」。

    否则刚练过的题会被当成 never 顶到队列第一位（复核单 P1-1）。
    """
    token, user_id = user
    question = _question(db, user_id, mastery="unmastered")
    old = _generated(db, user_id, question.id, deleted=True)
    live = _generated(db, user_id, question.id)
    _record(db, user_id, old.id, days_ago=5)

    body = _due(client, token)
    assert body["total"] == 1
    item = body["items"][0]
    assert item["last_practiced_at"] is not None
    assert item["due_reason"] == "unmastered_1d"
    # 软删的生成题不能返给前端，仍用未删除的那道
    assert item["generated_question"]["id"] == live.id
