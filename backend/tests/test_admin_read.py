"""ADM-003/007/011：管理端只读端点的越权与真实数据口径。"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import hash_password
from app.db.base import utcnow
from app.models import (
    AiCallLog,
    GeneratedQuestion,
    GenerationTask,
    PasswordResetRequest,
    PracticeRecord,
    Question,
    User,
)
from app.services.admin_actions import label
from tests.conftest import admin_headers, auth_headers, create_admin, register_user

READ_PATHS = [
    "/api/v1/admin/overview",
    "/api/v1/admin/users",
    "/api/v1/admin/tasks",
    "/api/v1/admin/ai-logs",
    "/api/v1/admin/audit",
    "/api/v1/admin/alerts",
    "/api/v1/admin/system",
    "/api/v1/admin/password-requests",
    # 详情端点单独覆盖：以后把端点挪出受保护 router 时，这里要能红
    "/api/v1/admin/users/999999",
    "/api/v1/admin/tasks/999999",
    "/api/v1/admin/ai-logs/999999",
    "/api/v1/admin/audit/999999",
    "/api/v1/admin/password-requests/999999",
]


def _seed(db):
    """两名学生（一个禁用）+ 题目/生成题/练习/任务/AI 日志/密码申请。"""
    session = db()
    try:
        alpha = User(
            username="alpha",
            email="alpha@example.com",
            password_hash=hash_password("p@ssw0rd9"),
        )
        beta = User(
            username="beta",
            email="beta@example.com",
            password_hash=hash_password("p@ssw0rd9"),
            disabled_at=utcnow(),
            disabled_reason="测试禁用",
        )
        session.add_all([alpha, beta])
        session.flush()

        question = Question(
            user_id=alpha.id,
            subject="高等数学",
            source_type="text",
            content_md="求函数 $f(x)=x^3-3x+1$ 的极值。",
            question_type="solve",
        )
        hidden = Question(
            user_id=alpha.id,
            subject="线性代数",
            source_type="text",
            content_md="已隐藏的题",
            question_type="solve",
            status="hidden",
        )
        deleted = Question(
            user_id=alpha.id,
            subject="线性代数",
            source_type="text",
            content_md="已删除的题",
            question_type="solve",
            deleted_at=utcnow(),
        )
        session.add_all([question, hidden, deleted])
        session.flush()

        generated = GeneratedQuestion(
            parent_question_id=question.id,
            user_id=alpha.id,
            content_md="相似题",
            answer_md="答案",
            explanation_md="解析",
        )
        session.add(generated)
        session.flush()
        session.add(
            PracticeRecord(
                user_id=alpha.id, generated_question_id=generated.id, is_correct=True
            )
        )

        now = utcnow()
        tasks = [
            GenerationTask(
                question_id=question.id,
                user_id=alpha.id,
                stage="analysis",
                status="failed",
                error_code="AI_TIMEOUT",
                error_message="超时",
                finished_at=now,
            ),
            GenerationTask(
                question_id=question.id,
                user_id=alpha.id,
                stage="quiz",
                status="failed",
                error_code="AI_TIMEOUT",
                finished_at=now,
            ),
            GenerationTask(
                question_id=question.id,
                user_id=alpha.id,
                stage="quiz",
                status="failed",
                error_code="AI_TIMEOUT",
                finished_at=now,
            ),
            GenerationTask(
                question_id=question.id,
                user_id=alpha.id,
                stage="analysis",
                status="queued",
            ),
            GenerationTask(
                question_id=question.id,
                user_id=alpha.id,
                stage="quiz",
                status="done",
                started_at=now - timedelta(seconds=30),
                finished_at=now,
            ),
        ]
        session.add_all(tasks)

        session.add_all(
            [
                AiCallLog(
                    user_id=alpha.id,
                    question_id=question.id,
                    operation="analyze",
                    model="deepseek-flash",
                    prompt_version="analyze_v3",
                    key_source="system",
                    input_tokens=1200,
                    output_tokens=300,
                    latency_ms=30_000,
                    queue_wait_ms=400,
                    status="success",
                    raw_response="原始输出",
                ),
                AiCallLog(
                    user_id=alpha.id,
                    operation="generate",
                    model="deepseek-flash",
                    prompt_version="quiz_v3",
                    key_source="system",
                    latency_ms=52_000,
                    status="error",
                    error_code="AI_TIMEOUT",
                ),
            ]
        )

        session.add(
            PasswordResetRequest(
                user_id=beta.id,
                username="beta",
                submitted_email="beta@example.com",
                reason="忘记密码",
                status="pending",
            )
        )
        session.commit()
    finally:
        session.close()


@pytest.mark.parametrize("path", READ_PATHS)
def test_student_token_is_rejected_on_every_read_endpoint(client, db, path):
    student = register_user(client, username="student01")
    resp = client.get(path, headers=auth_headers(student["access_token"]))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ADMIN_REQUIRED"

    assert client.get(path).status_code == 401


def test_overview_numbers_match_database(client, db):
    _seed(db)
    headers = admin_headers(client, db)

    body = client.get("/api/v1/admin/overview", headers=headers).json()
    stats = body["stats"]
    assert stats["users"] == {"total": 2, "active": 1, "disabled": 1, "new_7d": 2}
    assert stats["content"]["questions"] == 2  # 软删的不算
    assert stats["content"]["generated"] == 1
    assert stats["content"]["practice"] == 1
    assert stats["content"]["hidden"] == 1
    assert stats["ai"]["calls_24h"] == 2
    assert stats["ai"]["success_rate"] == 50.0
    assert stats["ai"]["p95_latency_ms"] == 52_000
    assert stats["ai"]["input_tokens"] == 1200
    assert stats["ai"]["estimated_cost"] is None
    assert stats["tasks"]["queued"] == 1
    assert stats["tasks"]["failed"] == 3
    assert stats["tasks"]["done_24h"] == 1
    assert stats["password_requests"]["pending"] == 1

    # 失败任务与待审批申请带真实数据，且 DTO 按前端 camelCase 输出
    assert len(body["failed_tasks"]) == 3
    failed = body["failed_tasks"][0]
    assert failed["code"] == f"T-{failed['id']}"
    assert failed["errorCode"] == "AI_TIMEOUT"
    assert failed["username"] == "alpha"
    assert body["pending_password_requests"][0]["username"] == "beta"

    alert_ids = {alert["id"] for alert in body["alerts"]}
    assert {"tasks_failed", "password_pending"} <= alert_ids
    assert len(body["trend"]["success"]) == 7


def test_users_list_filters_and_never_leaks_hash(client, db):
    _seed(db)
    headers = admin_headers(client, db)

    body = client.get("/api/v1/admin/users", headers=headers).json()
    assert body["total"] == 2
    assert {item["username"] for item in body["items"]} == {"alpha", "beta"}
    item = next(row for row in body["items"] if row["username"] == "alpha")
    assert item["createdAt"]
    assert item["lastLogin"] is None
    assert item["hasPersonalKey"] is False
    assert item["questions"] == 2  # 隐藏算，软删不算
    assert "password_hash" not in item

    disabled = client.get(
        "/api/v1/admin/users?status=disabled", headers=headers
    ).json()
    assert [row["username"] for row in disabled["items"]] == ["beta"]

    search = client.get("/api/v1/admin/users?q=alpha", headers=headers).json()
    assert [row["username"] for row in search["items"]] == ["alpha"]

    # 通配符必须被转义：`%` / `_` 不能当 LIKE 通配符用（复核单 §7.1）
    for wildcard in ("%", "_"):
        assert (
            client.get(
                "/api/v1/admin/users", params={"q": wildcard}, headers=headers
            ).json()["total"]
            == 0
        )

    # 管理员账号不进学生列表、也不能按 id 探
    admin = create_admin(client, db, username="admin02")
    me_id = client.get(
        "/api/v1/admin/me", headers=auth_headers(admin["access_token"])
    ).json()["id"]
    assert all(row["username"] != "admin02" for row in body["items"])
    assert (
        client.get(f"/api/v1/admin/users/{me_id}", headers=headers).status_code == 404
    )


def test_user_detail_includes_recent_tasks_and_requests(client, db):
    _seed(db)
    headers = admin_headers(client, db)
    users = client.get("/api/v1/admin/users", headers=headers).json()["items"]
    beta = next(row for row in users if row["username"] == "beta")
    alpha = next(row for row in users if row["username"] == "alpha")

    detail = client.get(f"/api/v1/admin/users/{beta['id']}", headers=headers).json()
    assert detail["status"] == "disabled"
    assert detail["disabledReason"] == "测试禁用"
    assert [row["username"] for row in detail["passwordRequests"]] == ["beta"]
    assert detail["passwordRequests"][0]["emailMatches"] is True
    assert detail["passwordRequests"][0]["usedAt"] is None

    alpha_detail = client.get(
        f"/api/v1/admin/users/{alpha['id']}", headers=headers
    ).json()
    assert len(alpha_detail["recentTasks"]) == 3


def test_tasks_list_and_timeline_use_real_fields(client, db):
    _seed(db)
    headers = admin_headers(client, db)

    failed = client.get("/api/v1/admin/tasks?status=failed", headers=headers).json()
    assert failed["total"] == 3
    task = failed["items"][0]
    assert task["duration"] == "—"  # 失败且没有 started_at
    assert task["createdAt"]
    assert "T-" in task["code"]

    done = client.get("/api/v1/admin/tasks?status=done", headers=headers).json()
    assert done["items"][0]["duration"] == "30 秒"

    queued = client.get("/api/v1/admin/tasks?status=queued", headers=headers).json()
    assert queued["items"][0]["duration"].startswith("等待 ")

    detail = client.get(f"/api/v1/admin/tasks/{task['id']}", headers=headers).json()
    assert [item["key"] for item in detail["timeline"]][0] == "created"
    assert {item["title"] for item in detail["timeline"]} >= {"任务入队", "执行失败"}

    search = client.get("/api/v1/admin/tasks?q=alpha", headers=headers).json()
    assert search["total"] == 5
    code = search["items"][0]["code"]
    assert client.get(f"/api/v1/admin/tasks?q={code}", headers=headers).json()["total"] == 1


def test_ai_logs_never_include_raw_and_format_display(client, db):
    _seed(db)
    headers = admin_headers(client, db)

    body = client.get("/api/v1/admin/ai-logs", headers=headers).json()
    assert body["total"] == 2
    success = next(row for row in body["items"] if row["status"] == "success")
    assert "raw" not in success
    assert success["hasRaw"] is True
    assert success["latency"] == "30.0s"
    assert success["queueWait"] == "0.4s"
    assert success["tokens"] == "1.5k"
    assert success["promptVersion"] == "analyze_v3"
    assert success["username"] == "alpha"

    errors = client.get(
        "/api/v1/admin/ai-logs?status=error", headers=headers
    ).json()
    assert errors["total"] == 1
    assert errors["items"][0]["tokens"] == "—"

    detail = client.get(
        f"/api/v1/admin/ai-logs/{success['id']}", headers=headers
    ).json()
    assert "raw" not in detail


def test_audit_search_matches_chinese_label_and_filters_result(client, db):
    _seed(db)
    headers = admin_headers(client, db)  # 登录本身写一条 admin.login

    body = client.get("/api/v1/admin/audit", headers=headers).json()
    assert body["total"] == 1
    log = body["items"][0]
    assert log["action"] == "admin.login"
    assert log["admin"] == "admin01"
    assert log["time"]
    assert label("admin.login") == "管理员登录"

    chinese = client.get(
        "/api/v1/admin/audit?q=管理员登录", headers=headers
    ).json()
    assert chinese["total"] == 1
    assert (
        client.get("/api/v1/admin/audit?q=不存在的词", headers=headers).json()["total"]
        == 0
    )

    detail = client.get(
        f"/api/v1/admin/audit/{log['id']}", headers=headers
    ).json()
    assert detail["id"] == log["id"]


def test_alerts_are_derived_and_include_target(client, db):
    _seed(db)
    headers = admin_headers(client, db)
    alerts = client.get("/api/v1/admin/alerts", headers=headers).json()
    assert isinstance(alerts, list)
    tasks = next(row for row in alerts if row["id"] == "tasks_failed")
    assert tasks["status"] == "active"
    assert tasks["current"] >= 3
    assert tasks["target"]["to"] == "/tasks?status=failed"
    assert tasks["acknowledgedBy"] is None


def test_system_reports_real_environment_and_no_secrets(client, db):
    _seed(db)
    headers = admin_headers(client, db)
    body = client.get("/api/v1/admin/system", headers=headers).json()

    assert body["environment"]["app_env"] == "development"
    assert body["environment"]["is_demo"] is True  # 测试强制 LLM_MOCK
    assert body["environment"]["database"] == "sqlite"
    assert body["generated_at"]
    keys = {check["key"] for check in body["checks"]}
    assert keys == {"api", "database", "worker", "llm"}
    assert all(check["checkedAt"] for check in body["checks"])
    assert body["events"]  # 真实事件（任务/AI/审计）

    raw = str(body)
    assert "jwt_secret" not in raw.lower()
    assert "password_hash" not in raw.lower()
