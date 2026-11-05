"""健康检查、错误信封与探活行为（BE-001 验收项 + issue #11 follow-up）。

/health 现在真的连库（13号 §4.2）：这里用临时 SQLite 和坏 URL 两种引擎覆盖
「可用 → 200」和「不可用 → 503」两条路径。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.errors import ErrorCode
from app.core.observability import REQUEST_ID_HEADER
from app.db import session as db_session
from app.main import app

client = TestClient(app)


@pytest.fixture()
def good_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'health.db').as_posix()}")
    monkeypatch.setattr(db_session, "engine", engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def dead_engine(monkeypatch):
    """指向一个不存在的 MySQL 端口；探活必须把它报成 unavailable 而不是抛异常。"""
    engine = create_engine("mysql+pymysql://nobody:nothing@127.0.0.1:1/nope")
    monkeypatch.setattr(db_session, "engine", engine)
    yield engine
    engine.dispose()


def test_health_checks_database_for_real(good_engine) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["db"] == "ok"


def test_health_returns_503_when_database_unreachable(dead_engine) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 503
    assert resp.json()["db"] == "unavailable"


def test_ready_reports_llm_config_without_calling_llm(good_engine) -> None:
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200, resp.text
    checks = resp.json()["checks"]
    assert checks["db"] == "ok"
    assert checks["llm"] == "mock"  # 测试环境不配 Key，mock 模式就是就绪的


def test_ready_returns_503_when_llm_key_missing(good_engine, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_mock", False)
    monkeypatch.setattr(settings, "llm_api_key", "")
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"]["llm"] == "missing_key"


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


def test_method_not_allowed_is_not_reported_as_validation_error() -> None:
    """13号 §4.8：405 曾被统统标成 VALIDATION_ERROR，前端会误以为参数写错了。"""
    resp = client.put("/api/v1/health")
    assert resp.status_code == 405
    assert resp.json()["detail"]["code"] == str(ErrorCode.METHOD_NOT_ALLOWED)


def test_cors_allows_configured_origin() -> None:
    resp = client.get(
        "/api/v1/health", headers={"Origin": "http://localhost:5173"}
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_startup_refuses_to_boot_without_jwt_secret() -> None:
    """issue #11 BE-003：JWT_SECRET 缺失要在启动时报清楚，而不是等第一个登录请求 500。"""
    from app.core.config import Settings

    broken = Settings(_env_file=None, jwt_secret="", llm_mock=True)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        broken.validate_for_startup()

    no_key = Settings(_env_file=None, jwt_secret="x" * 32, llm_mock=False, llm_api_key="")
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        no_key.validate_for_startup()
