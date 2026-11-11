"""BE-013 契约：GET /stats/overview（05 §6.6 / 21号 §2.1）。

种子直接写库（不走 API）：练习/生成的时间与判定、软删、父题缺失这些边界
从接口造不出来，也没必要为了统计再绕一圈业务校验。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.base import utcnow
from app.models import GeneratedQuestion, GenerationTask, PracticeRecord, Question, Tag
from app.services.stats_service import CHINA_TZ, TREND_DAYS
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def user(client: TestClient) -> tuple[str, int]:
    data = register_user(client)
    return data["access_token"], data["user"]["id"]


def _overview(client: TestClient, token: str) -> dict:
    resp = client.get("/api/v1/stats/overview", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _tag(session, name: str) -> Tag:
    tag = Tag(name=name, type="knowledge_point")
    session.add(tag)
    return tag


def _question(
    session,
    user_id: int,
    *,
    content: str = "题干",
    tags: list[Tag] | None = None,
    mastery: str = "unmastered",
    deleted: bool = False,
    updated_at: datetime | None = None,
) -> Question:
    question = Question(
        user_id=user_id,
        subject="数学",
        content_md=content,
        question_type="solve",
        mastery_status=mastery,
        deleted_at=utcnow() if deleted else None,
    )
    if updated_at is not None:
        question.updated_at = updated_at
    question.tags = list(tags or [])
    session.add(question)
    session.flush()
    return question


def _generated(
    session, user_id: int, parent: Question, *, deleted: bool = False
) -> GeneratedQuestion:
    item = GeneratedQuestion(
        parent_question_id=parent.id,
        user_id=user_id,
        content_md="相似题",
        answer_md="答案",
        explanation_md="解析",
        question_type="solve",
        deleted_at=utcnow() if deleted else None,
    )
    session.add(item)
    session.flush()
    return item


def _record(
    session,
    user_id: int,
    generated: GeneratedQuestion,
    *,
    is_correct: bool,
    created_at: datetime | None = None,
) -> PracticeRecord:
    record = PracticeRecord(
        user_id=user_id,
        generated_question_id=generated.id,
        user_answer="作答",
        is_correct=is_correct,
        duration_seconds=30,
    )
    if created_at is not None:
        record.created_at = created_at
    session.add(record)
    session.flush()
    return record


def test_empty_overview(client: TestClient, user) -> None:
    token, _ = user
    body = _overview(client, token)

    assert body["total_questions"] == 0
    assert body["total_generated_questions"] == 0
    assert body["total_practice_records"] == 0
    assert body["accuracy"] == 0  # 契约：无记录返回 0，不是 null
    assert body["mastered_count"] == body["reviewing_count"] == body["unmastered_count"] == 0
    assert body["weak_knowledge_points"] == []
    assert body["recent_trend"] == []
    # 空账号也得给一个可解析的时间，前端"更新于"不能显示 Invalid Date
    assert body["updated_at"].endswith("Z")
    datetime.fromisoformat(body["updated_at"].replace("Z", "+00:00"))


def test_counts_accuracy_and_mastery_sum(client: TestClient, db, user) -> None:
    token, user_id = user
    with db() as s:
        q1 = _question(s, user_id, content="题一", mastery="mastered")
        _question(s, user_id, content="题二", mastery="reviewing")
        _question(s, user_id, content="题三")
        generated = _generated(s, user_id, q1)
        _record(s, user_id, generated, is_correct=True)
        _record(s, user_id, generated, is_correct=True)
        _record(s, user_id, generated, is_correct=False)
        s.commit()

    body = _overview(client, token)
    assert body["total_questions"] == 3
    assert body["total_generated_questions"] == 1
    assert body["total_practice_records"] == 3
    assert body["accuracy"] == 0.667  # 2/3，三位小数
    assert body["mastered_count"] == 1
    assert body["reviewing_count"] == 1
    assert body["unmastered_count"] == 1
    assert (
        body["mastered_count"] + body["reviewing_count"] + body["unmastered_count"]
        == body["total_questions"]
    )


def test_weak_points_aggregate_order_and_top5(client: TestClient, db, user) -> None:
    """错得多在前 → 正确率低在前 → 练习量大的在前；没练过的标签不收；最多 5 条。"""
    token, user_id = user
    with db() as s:
        tags = [
            _tag(s, name) for name in ("导数", "极限", "积分", "概率", "线代", "级数", "几何")
        ]
        generated_by_parent = {}
        for position, tag in enumerate(tags):
            parent = _question(s, user_id, content=f"题{position}", tags=[tag])
            generated_by_parent[tag.name] = _generated(s, user_id, parent)

        def practice(tag_name: str, *, correct: int, wrong: int) -> None:
            for _ in range(correct):
                _record(s, user_id, generated_by_parent[tag_name], is_correct=True)
            for _ in range(wrong):
                _record(s, user_id, generated_by_parent[tag_name], is_correct=False)

        practice("导数", correct=0, wrong=2)  # 错 2 次：排第一
        practice("极限", correct=1, wrong=1)  # 错 1 次、正确率 0.5
        practice("积分", correct=2, wrong=0)  # 错 0、正确率 1
        practice("概率", correct=0, wrong=1)  # 错 1 次、正确率 0：排在极限前
        practice("线代", correct=3, wrong=0)
        practice("几何", correct=1, wrong=0)  # 第 6 条有练习的标签，Top 5 之外被截掉
        # 级数：有题、有标签、零练习 → 不出现
        s.commit()

    body = _overview(client, token)
    weak = body["weak_knowledge_points"]
    assert [point["name"] for point in weak] == ["导数", "概率", "极限", "线代", "积分"]
    assert weak[0] == {"name": "导数", "wrong_count": 2, "total_count": 2, "accuracy": 0.0}
    assert weak[1] == {"name": "概率", "wrong_count": 1, "total_count": 1, "accuracy": 0.0}
    assert weak[2] == {"name": "极限", "wrong_count": 1, "total_count": 2, "accuracy": 0.5}


def test_soft_deleted_question_excluded(client: TestClient, db, user) -> None:
    """删错题不级联生成题（真实行为），统计必须自己按"父题活着"收口。

    练习流水没有 deleted_at：total_practice_records 照算，薄弱点不再聚合。
    """
    token, user_id = user
    with db() as s:
        alive_tag = _tag(s, "导数")
        dead_tag = _tag(s, "极限")
        alive = _question(s, user_id, tags=[alive_tag])
        dead = _question(s, user_id, content="已删题", tags=[dead_tag], deleted=True)
        alive_generated = _generated(s, user_id, alive)
        orphan_generated = _generated(s, user_id, dead)  # 父题已删、自己还活着
        _record(s, user_id, alive_generated, is_correct=True)
        _record(s, user_id, orphan_generated, is_correct=False)
        s.commit()

    body = _overview(client, token)
    assert body["total_questions"] == 1
    assert body["total_generated_questions"] == 1  # 孤儿生成题不计数
    assert body["total_practice_records"] == 2  # 流水不随错题消失
    assert [point["name"] for point in body["weak_knowledge_points"]] == ["导数"]


def _shanghai_midnight_utc(days_ago: int) -> tuple[datetime, str]:
    """上海「N 天前」00:00 对应的 UTC naive 时间，以及那天的日期串。"""
    day = datetime.now(UTC).astimezone(CHINA_TZ).date() - timedelta(days=days_ago)
    start = datetime(day.year, day.month, day.day, tzinfo=CHINA_TZ)
    return start.astimezone(UTC).replace(tzinfo=None), day.isoformat()


def test_recent_trend_uses_shanghai_days(client: TestClient, db, user) -> None:
    """按上海日期切天，且只取最近 7 天；昨天 23:59 与今天 00:01 分属两天。"""
    token, user_id = user
    yesterday_2359, yesterday = _shanghai_midnight_utc(1)
    today_0001, today = _shanghai_midnight_utc(0)
    day_before, day_before_date = _shanghai_midnight_utc(2)
    too_old, too_old_date = _shanghai_midnight_utc(TREND_DAYS)
    with db() as s:
        parent = _question(s, user_id)
        generated = _generated(s, user_id, parent)
        for created_at in (
            yesterday_2359 + timedelta(hours=23, minutes=59),
            today_0001 + timedelta(minutes=1),
            day_before + timedelta(hours=10),
            too_old + timedelta(hours=10),
        ):
            _record(s, user_id, generated, is_correct=True, created_at=created_at)
        s.commit()

    body = _overview(client, token)
    assert body["recent_trend"] == [
        {"date": day_before_date, "practice_count": 1, "correct_count": 1},
        {"date": yesterday, "practice_count": 1, "correct_count": 1},
        {"date": today, "practice_count": 1, "correct_count": 1},
    ]
    assert too_old_date not in [point["date"] for point in body["recent_trend"]]


def test_updated_at_tracks_latest_visible_change(client: TestClient, db, user) -> None:
    """题目早已不动，最近一次生题任务完成才是"数据更新于"。"""
    token, user_id = user
    finished = utcnow() - timedelta(minutes=5)
    with db() as s:
        parent = _question(s, user_id, updated_at=utcnow() - timedelta(days=3))
        s.add(
            GenerationTask(
                question_id=parent.id,
                user_id=user_id,
                stage="quiz",
                status="done",
                target_index=1,
                created_at=finished - timedelta(minutes=2),
                finished_at=finished,
            )
        )
        s.commit()

    body = _overview(client, token)
    assert body["updated_at"] == finished.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def test_user_isolation(client: TestClient, db, user) -> None:
    token, user_id = user
    with db() as s:
        parent = _question(s, user_id)
        generated = _generated(s, user_id, parent)
        _record(s, user_id, generated, is_correct=True)
        s.commit()

    other = register_user(client, username="隔壁同学")
    body = _overview(client, other["access_token"])
    assert body["total_questions"] == 0
    assert body["total_practice_records"] == 0
    assert body["weak_knowledge_points"] == []
    assert body["recent_trend"] == []


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/stats/overview").status_code == 401


def test_soft_deleted_generated_excluded_from_count(client: TestClient, db, user) -> None:
    """父题活着、生成题自己软删：题数不计；练习流水照算，薄弱点仍按父题聚合。"""
    token, user_id = user
    with db() as s:
        parent = _question(s, user_id, tags=[_tag(s, "导数")])
        gone = _generated(s, user_id, parent, deleted=True)
        _record(s, user_id, gone, is_correct=False)
        s.commit()

    body = _overview(client, token)
    assert body["total_questions"] == 1
    assert body["total_generated_questions"] == 0
    assert body["total_practice_records"] == 1
    assert [point["name"] for point in body["weak_knowledge_points"]] == ["导数"]
