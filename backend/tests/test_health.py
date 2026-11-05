"""健康检查与错误信封的测试（BE-001 验收项：`/health` + CORS + 日志 + ruff + pytest）。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.errors import ErrorCode
from app.core.observability import REQUEST_ID_HEADER
from app.main import app

client = TestClient(app)


def test_health_reports_version_and_db_state() -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    # BE-001 还没接数据库，所以这里必须是 not_configured 而不是假装能连
    assert body["db"] == "not_configured"


def test_response_carries_request_id_header() -> None:
    resp = client.get("/api/v1/health")
    assert resp.headers[REQUEST_ID_HEADER].startswith("req_")


def test_upstream_request_id_is_reused() -> None:
    resp = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: "req_frontend_1"})
    assert resp.headers[REQUEST_ID_HEADER] == "req_frontend_1"


def test_unknown_path_uses_the_same_error_envelope() -> None:
    resp = client.get("/")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == str(ErrorCode.NOT_FOUND)
    assert detail["request_id"].startswith("req_")
    assert "message" in detail


def test_cors_allows_configured_origin() -> None:
    resp = client.get(
        "/api/v1/health", headers={"Origin": "http://localhost:5173"}
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
