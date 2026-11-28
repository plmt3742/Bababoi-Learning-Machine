"""BE-030 全局改密门禁（复核单 §11.2）。

口径：门禁在 `get_current_user` 里默认拒绝；白名单只有 `/auth/me`、
`/auth/change-password`、`/auth/logout` 三个端点，用端点标记而不是路径匹配。
"""
from __future__ import annotations

import re

from fastapi.routing import APIRoute

from app.main import app
from app.models import User
from tests.conftest import auth_headers, create_admin, register_user

LOCKED_PATHS = [
    "/api/v1/questions",
    "/api/v1/tasks",
    "/api/v1/drafts/me",
    "/api/v1/stats/overview",
    "/api/v1/practice-records",
    "/api/v1/settings/ai",
    "/api/v1/settings/preferences",
]

PUBLIC_GET = {"/api/v1/health", "/api/v1/ready"}


def _set_flag(db, user_id: int, value: bool = True) -> None:
    session = db()
    try:
        session.get(User, user_id).must_change_password = value
        session.commit()
    finally:
        session.close()


def test_flag_blocks_business_endpoints_but_allows_gate_whitelist(client, db):
    body = register_user(client, username="student01")
    token = body["access_token"]
    _set_flag(db, body["user"]["id"])

    for path in LOCKED_PATHS:
        resp = client.get(path, headers=auth_headers(token))
        assert resp.status_code == 403, (path, resp.status_code, resp.text)
        assert resp.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    # 白名单：读标记
    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    # 白名单：退出（学生登出不吊销版本，仍可继续用 token）
    assert (
        client.post("/api/v1/auth/logout", headers=auth_headers(token)).status_code
        == 204
    )


def test_change_password_clears_flag_and_revokes_old_token(client, db):
    body = register_user(client, username="student01", password="p@ssw0rd9")
    token = body["access_token"]
    _set_flag(db, body["user"]["id"])

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "p@ssw0rd9", "new_password": "n3w-p@ssw0rd"},
        headers=auth_headers(token),
    )
    assert changed.status_code == 204, changed.text

    old = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert old.status_code == 401
    assert old.json()["detail"]["code"] == "AUTH_TOKEN_EXPIRED"

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "student01", "password": "n3w-p@ssw0rd"},
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"] is False
    new_token = login.json()["access_token"]

    assert client.get("/api/v1/questions", headers=auth_headers(new_token)).status_code == 200


def test_admin_token_is_not_gated(client, db):
    admin = create_admin(client, db)
    resp = client.get(
        "/api/v1/admin/me", headers=auth_headers(admin["access_token"])
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is False


def test_exempt_endpoints_are_exactly_the_three_whitelisted():
    from app.api.v1 import auth as auth_module

    exempt = {
        route.endpoint
        for route in auth_module.router.routes
        if isinstance(route, APIRoute)
        and getattr(route.endpoint, "__password_gate_exempt__", False)
    }
    assert exempt == {
        auth_module.me,
        auth_module.change_password,
        auth_module.logout,
    }


def test_every_authenticated_get_route_rejects_missing_token(client):
    """兜底：除健康检查外，OpenAPI 里所有 GET 都必须先要登录（新增端点漏挂鉴权会红）。"""
    spec = app.openapi()
    for path, operations in spec["paths"].items():
        if "get" not in operations:
            continue
        url = re.sub(r"\{[^}]+\}", "1", path)
        resp = client.get(url)
        if path in PUBLIC_GET:
            assert resp.status_code == 200, (path, resp.status_code)
        else:
            assert resp.status_code == 401, (path, resp.status_code, resp.text)
