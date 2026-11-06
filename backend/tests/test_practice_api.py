"""BE-012 契约：POST/GET /practice-records + 防重复窗口。"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.base import utcnow
from app.models import GeneratedQuestion, PracticeRecord, Question
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def user(client: TestClient) -> tuple[str, int]:
    data = register_user(client)
    return data["access_token"], data["user"]["id"]


@pytest.fixture()
def generated_question(db, user) -> GeneratedQuestion:
    _, user_id = user
    with db() as s:
        gq = GeneratedQuestion(
            parent_question_id=1,
            user_id=user_id,
            content_md="求 $g(x)=x^3-3x$ 的单调区间。",
            answer_md="增区间 $(-\\infty,-1)\\cup(1,+\\infty)$",
            explanation_md="求导即可。",
            question_type="solve",
        )
        # parent_question_id 有 FK，先补一道原题
        s.add(
            Question(
                user_id=user_id,
                subject="数学",
                content_md="f(x)=x³-3x 的极大值点是？",
                question_type="solve",
            )
        )
        s.flush()
        gq.parent_question_id = s.scalars(select(Question.id)).first()
        s.add(gq)
        s.commit()
        return gq


def _post(client, token, **overrides) -> dict:
    body = {
        "generated_question_id": 1,
        "user_answer": "增(-∞,-1)∪(1,+∞)，减(-1,1)",
        "is_correct": True,
        "duration_seconds": 45,
    }
    body.update(overrides)
    return client.post("/api/v1/practice-records", json=body, headers=auth_headers(token))


def test_create_and_get_record(client, db, user, generated_question) -> None:
    token, _ = user
    resp = _post(client, token)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["generated_question_id"] == generated_question.id
    assert body["is_correct"] is True
    assert body["duration_seconds"] == 45

    page = client.get(
        "/api/v1/practice-records",
        params={"generated_question_id": generated_question.id},
        headers=auth_headers(token),
    ).json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == body["id"]


def test_duplicate_within_window_rejected(client, db, user, generated_question) -> None:
    """同用户+同生成题+同答案+同判定，60 秒内重复提交 → 409 PRACTICE_DUPLICATE。"""
    token, _ = user
    assert _post(client, token).status_code == 201
    resp = _post(client, token, duration_seconds=52)  # 只有时长不同，仍算重复
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PRACTICE_DUPLICATE"


def test_repeat_after_window_allowed(client, db, user, generated_question) -> None:
    """窗口外的重练是正常使用：人工把上一条挪出 60 秒窗口再提交应成功。"""
    token, user_id = user
    assert _post(client, token).status_code == 201
    with db() as s:
        record = s.get(PracticeRecord, 1)
        record.created_at = utcnow() - timedelta(seconds=120)
        s.commit()
    resp = _post(client, token, duration_seconds=80)
    assert resp.status_code == 201, resp.text
    with db() as s:
        assert (
            s.scalar(select(PracticeRecord.id).where(PracticeRecord.user_id == user_id))
            is not None
        )


def test_different_answer_not_duplicate(client, db, user, generated_question) -> None:
    token, _ = user
    assert _post(client, token).status_code == 201
    resp = _post(client, token, is_correct=False, user_answer="答错了")
    assert resp.status_code == 201, resp.text


def test_cannot_record_on_other_users_generated(client, db, generated_question) -> None:
    """b 对 a 的生成题提交 → 404（不区分不存在/越权，防枚举）。"""
    token_b = register_user(client, username="other_user")["access_token"]
    resp = _post(client, token_b)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_duration_out_of_range_rejected(client, db, user, generated_question) -> None:
    token, _ = user
    assert _post(client, token, duration_seconds=3601).status_code == 400
    assert _post(client, token, duration_seconds=-1).status_code == 400


def test_records_isolated_between_users(client, db, user, generated_question) -> None:
    token, _ = user
    assert _post(client, token).status_code == 201
    token_b = register_user(client, username="viewer_user")["access_token"]
    page = client.get("/api/v1/practice-records", headers=auth_headers(token_b)).json()
    assert page["total"] == 0


def test_practice_does_not_change_mastery_status(client, db, user, generated_question) -> None:
    """确认单 B-5 的另一半：答对也不自动升掌握状态，前端要改就 PATCH /questions/{id}。"""
    token, _ = user
    qid = generated_question.parent_question_id
    assert _post(client, token, is_correct=True).status_code == 201
    detail = client.get(f"/api/v1/questions/{qid}", headers=auth_headers(token)).json()
    assert detail["mastery_status"] == "unmastered"


def test_record_on_regenerated_old_question_is_gone(client, db, user, generated_question) -> None:
    """整组重生成会软删旧题（BE-006/007 的替换语义），对旧题补交应当 404。"""
    token, _ = user
    with db() as s:
        # fixture 给的是游离对象，直接改它不会落库——要在本次 session 里重新取
        s.get(GeneratedQuestion, generated_question.id).deleted_at = utcnow()
        s.commit()
    resp = _post(client, token)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"
