"""BE-026 生成偏好：设置接口 + 生成链路按偏好执行硬/软校验（issue #44）。"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime

import pytest
from sqlalchemy import select

import app.api.v1.settings as settings_api
from app.ai.client import _MOCK_QUIZ_SEGMENTS, OPERATION_QUIZ, MockLLMClient
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
    """原题是解答题。"""
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


class _ForcedTypeClient(MockLLMClient):
    """第 1 段强制出填空、第 3 段强制出选择。

    mock 自 2026-11-10 起跟随原题题型，不再天然产生错配；验 strict 的判死能力
    只能自己造——否则这个测试会在 mock 与开关同时"正确"时永远走不到失败分支。
    """

    def complete(self, operation, messages):
        resp = super().complete(operation, messages)
        if operation != OPERATION_QUIZ:
            return resp
        user = messages[-1]["content"]
        forced = {"第 1 道": ("blank", "easy"), "第 3 道": ("choice", "hard")}
        key = next((card for marker, card in forced.items() if marker in user), None)
        if key is None:
            return resp
        return replace(resp, text=json.dumps(_MOCK_QUIZ_SEGMENTS[key], ensure_ascii=False))


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
    fake_llm["client"] = _ForcedTypeClient()

    def post_generate() -> list[int]:
        return [t["task_id"] for t in client.post(
            f"/api/v1/questions/{qid}/generate", json={}, headers=auth_headers(token)
        ).json()["tasks"]]

    def run_pass(task_ids: list[int]) -> None:
        # 只消费 queued：done/failed 的段再跑一遍等于重复调 LLM，测不出 requeue
        with db() as s:
            queued = [tid for tid in task_ids if s.get(GenerationTask, tid).status == "queued"]
        for tid in queued:
            task_worker.execute_task(db, tid)

    def segments_state(task_ids: list[int]) -> dict[int, tuple[str, int]]:
        with db() as s:
            rows = list(s.scalars(select(GenerationTask).where(GenerationTask.id.in_(task_ids))))
        return {t.target_index: (t.status, t.retry_index) for t in rows}

    strict_ids = post_generate()
    run_pass(strict_ids)
    first_pass = segments_state(strict_ids)
    assert first_pass[2] == ("done", 0), "第 2 段 mock 输出就是 solve，与原题一致 → 必须成功"
    assert first_pass[1] == ("queued", 1) and first_pass[3] == ("queued", 1),         "strict 判死后必须走任务级 requeue（queued + retry_index=1），而不是直接 failed"

    run_pass(strict_ids)
    second_pass = segments_state(strict_ids)
    assert second_pass[1][0] == "failed" and second_pass[3][0] == "failed",         "重试一次后仍不一致 → failed"
    with db() as s:
        alive = list(s.scalars(select(GeneratedQuestion).where(
            GeneratedQuestion.parent_question_id == qid,
            GeneratedQuestion.deleted_at.is_(None))))
        assert [g.target_index for g in alive] == [2], "只有一格能落库"
        assert [g.prompt_version for g in alive] == ["generate_v3"],             "strict 的输出必须记成 generate_v3，否则日志分不清是哪版 prompt"

    # 关掉开关：同样三段输出全部入库
    assert _put_prefs(client, token, {"enforce_same_question_type": False}).status_code == 200
    soft_ids = post_generate()
    run_pass(soft_ids)
    assert {status for status, _ in segments_state(soft_ids).values()} == {"done"}


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
        assert {log.prompt_version for log in quiz_logs} == {"generate_v3"}, \
            "strict 用的是 generate_v3 的 prompt 文本"
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
        soft_logs = [log for log in recent if log.type_policy == "soft"]
        assert soft_logs, "关闭后必须记成 soft"
        assert {log.prompt_version for log in soft_logs} == {"generate_v2"}, \
            "soft 的 prompt 没变，仍记 generate_v2"

def test_preferences_updated_at_ignores_login(client, db, fake_llm, monkeypatch) -> None:
    """设置页"最近更新"只跟偏好写入走；登录写 last_login_at 不能让它跳变。

    PUT 后的时间戳用固定值断言，不靠"两次 utcnow 必然不同"——高速 CI 上那是 flaky。
    """
    data = register_user(client)
    token = data["access_token"]
    before = _get_prefs(client, token)["updated_at"]

    resp = client.post("/api/v1/auth/login", json={
        "username": data["user"]["username"], "password": "p@ssw0rd9",
    })
    assert resp.status_code == 200, resp.text
    assert _get_prefs(client, token)["updated_at"] == before

    fixed = datetime(2030, 1, 2, 3, 4, 5, 123456)
    monkeypatch.setattr(settings_api, "utcnow", lambda: fixed)
    put = _put_prefs(client, token, {"enforce_same_question_type": False})
    assert put.status_code == 200
    assert put.json()["updated_at"] == "2030-01-02T03:04:05.123456"
    assert _get_prefs(client, token)["updated_at"] == "2030-01-02T03:04:05.123456"
