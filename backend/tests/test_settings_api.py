"""BE-026 生成偏好：设置接口 + 生成链路按偏好执行硬/软校验（issue #44）。"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai.client import MockLLMClient
from app.models import AiCallLog, GeneratedQuestion, GenerationTask
from app.services import task_worker
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def fake_llm(monkeypatch):
    holder = {"client": MockLLMClient()}
    monkeypatch.setattr(task_worker, "_llm_client", lambda: holder["client"])
    return holder


def _get_prefs(client, token):
    resp = client.get("/api/v1/settings/preferences", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _put_prefs(client, token, body):
    return client.put("/api/v1/settings/preferences", json=body, headers=auth_headers(token))


def _solve_question(client, token):
    """原题是解答题——mock 的三段分别输出 blank/solve/choice，正好能验硬校验。"""
    resp = client.post(
        "/api/v1/questions",
        json={
            "subject": "高等数学",
            "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
            "question_type": "solve",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["question"]["id"]


def test_preferences_default_true_for_new_user(client) -> None:
    token = register_user(client)["access_token"]
    body = _get_prefs(client, token)
    assert body["enforce_same_question_type"] is True, "默认开启是产品决策，新用户必须是 true"
    assert body["updated_at"], "前端保存提示要读这一项"


def test_preferences_roundtrip_persists(client) -> None:
    token = register_user(client)["access_token"]
    assert _put_prefs(client, token, {"enforce_same_question_type": False}).status_code == 200
    assert _get_prefs(client, token)["enforce_same_question_type"] is False, "换请求（同 token 重取）必须仍是关"


def test_preferences_missing_field_falls_back_to_true(client) -> None:
    """PUT 不带字段 = 用默认值，不能理解成"关掉"或"保持原值"。"""
    token = register_user(client)["access_token"]
    _put_prefs(client, token, {"enforce_same_question_type": False})
    body = _put_prefs(client, token, {}).json()
    assert body["enforce_same_question_type"] is True


def test_preferences_rejects_non_boolean(client) -> None:
    """非布尔必须是错误，不能被 pydantic 悄悄转成 true。

    状态码是 400 不是 422：本项目的异常处理器把请求校验失败统一收成
    `400 VALIDATION_ERROR`（05 §6.2），前端只按这一种形状读错误。
    """
    token = register_user(client)["access_token"]
    resp = _put_prefs(client, token, {"enforce_same_question_type": "yes"})
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"
    # 被拒之后原值不能变
    assert _get_prefs(client, token)["enforce_same_question_type"] is True


def test_preferences_require_auth(client) -> None:
    assert client.get("/api/v1/settings/preferences").status_code == 401
    assert client.put("/api/v1/settings/preferences",
                      json={"enforce_same_question_type": False}).status_code == 401


def test_preferences_are_isolated_per_user(client) -> None:
    a = register_user(client, username="prefA")["access_token"]
    b = register_user(client, username="prefB")["access_token"]
    _put_prefs(client, a, {"enforce_same_question_type": False})
    assert _get_prefs(client, b)["enforce_same_question_type"] is True, "A 的开关不能影响 B"


def test_strict_policy_rejects_type_mismatch_and_soft_allows(client, db, fake_llm) -> None:
    """开关开启：题型与原题不一致的段重试 1 次后失败；关闭：照常入库。

    判据放在 validate_segment、重试交给现有任务级 requeue——不在 pipeline 里再叠一层，
    否则三段并发下最坏变成 3 次/段 × 3 段 = 9 次 LLM 调用。
    """
    token = register_user(client)["access_token"]
    qid = _solve_question(client, token)

    def run_segments():
        tasks = client.post(
            f"/api/v1/questions/{qid}/generate", json={}, headers=auth_headers(token)
        ).json()["tasks"]
        for _ in range(2):
            for t in tasks:
                task_worker.execute_task(db, t["task_id"])
        with db() as s:
            rows = list(s.scalars(select(GenerationTask).where(GenerationTask.id.in_(
                [t["task_id"] for t in tasks]))))
        return tasks, {t.target_index: t.status for t in rows}

    strict_tasks, strict_status = run_segments()
    assert strict_status[2] == "done", "第 2 段 mock 输出就是 solve，与原题一致 → 必须成功"
    assert strict_status[1] == "failed" and strict_status[3] == "failed", \
        "第 1 段 blank、第 3 段 choice 与原题 solve 不一致 → 重试后失败"
    with db() as s:
        alive = list(s.scalars(select(GeneratedQuestion).where(
            GeneratedQuestion.parent_question_id == qid,
            GeneratedQuestion.deleted_at.is_(None))))
        assert [g.target_index for g in alive] == [2], "只有一格能落库"

    # 关掉开关：同样三段输出全部入库
    assert _put_prefs(client, token, {"enforce_same_question_type": False}).status_code == 200
    client.post(f"/api/v1/questions/{qid}/generate", json={}, headers=auth_headers(token))
    _, soft_status = run_segments()
    assert set(soft_status.values()) == {"done"}, soft_status


def test_call_log_records_type_policy(client, db, fake_llm) -> None:
    """按策略分组才能量"默认开启值不值"——这一列没记，失败率就只能靠猜。"""
    token = register_user(client)["access_token"]
    qid = _solve_question(client, token)
    tasks = client.post(
        f"/api/v1/questions/{qid}/generate", json={}, headers=auth_headers(token)
    ).json()["tasks"]
    for t in tasks:
        task_worker.execute_task(db, t["task_id"])

    with db() as s:
        quiz_logs = list(s.scalars(select(AiCallLog).where(AiCallLog.operation == "quiz")))
        assert quiz_logs, "quiz 调用必须有日志"
        assert {log.type_policy for log in quiz_logs} == {"strict"}
        analysis_logs = list(s.scalars(select(AiCallLog).where(AiCallLog.operation == "analysis")))
        assert all(log.type_policy is None for log in analysis_logs), "非 quiz 操作不写这一列"

    _put_prefs(client, token, {"enforce_same_question_type": False})
    tasks = client.post(
        f"/api/v1/questions/{qid}/generate", json={}, headers=auth_headers(token)
    ).json()["tasks"]
    for t in tasks:
        task_worker.execute_task(db, t["task_id"])
    with db() as s:
        recent = list(s.scalars(select(AiCallLog).where(AiCallLog.operation == "quiz")))
        assert any(log.type_policy == "soft" for log in recent), "关闭后必须记成 soft"
