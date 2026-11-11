"""BE-018 契约：GET/PUT/DELETE /drafts/me（05 §6.5b / 21号 §2.2）。

对齐口径是前端 mock（`frontend/src/api/mocks/index.ts`）：
- content 必须是 JSON 对象（非对象 400）；
- 无草稿时 `base_version` 不参与判断，直接建 v1；
- 有草稿时 `version != base_version`（含 null）→ 409 `DRAFT_VERSION_CONFLICT`；
- 409 用统一错误信封，不回传服务端草稿。
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user

ENDPOINT = "/api/v1/drafts/me"


@pytest.fixture()
def user(client: TestClient) -> tuple[str, int]:
    data = register_user(client)
    return data["access_token"], data["user"]["id"]


def _put(client: TestClient, token: str, body: dict) -> dict:
    resp = client.put(ENDPOINT, json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_get_empty_returns_204(client: TestClient, user) -> None:
    token, _ = user
    resp = client.get(ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 204
    assert resp.content == b""


def test_put_creates_and_get_roundtrip(client: TestClient, user) -> None:
    token, _ = user
    content = {"question_type": "solve", "content_md": "题干", "tags": ["导数"]}
    body = _put(client, token, {"content": content, "base_version": 0, "client_updated_at": "2026-11-11T08:00:00Z"})
    assert body["version"] == 1
    assert body["content"] == content
    # 前端拿 updated_at 和 localStorage 比"哪边更新"：没有 Z 会被按本地时区解析
    assert body["updated_at"].endswith("Z")

    got = client.get(ENDPOINT, headers=auth_headers(token))
    assert got.status_code == 200
    assert got.json() == body


def test_put_bumps_version_with_matching_base(client: TestClient, user) -> None:
    token, _ = user
    _put(client, token, {"content": {"a": 1}, "base_version": 0})
    body = _put(client, token, {"content": {"a": 2}, "base_version": 1})
    assert body["version"] == 2
    assert body["content"] == {"a": 2}


def test_stale_base_version_conflicts(client: TestClient, user) -> None:
    token, _ = user
    _put(client, token, {"content": {"a": 1}, "base_version": 0})
    resp = client.put(ENDPOINT, json={"content": {"a": 2}, "base_version": 0},
                      headers=auth_headers(token))
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "DRAFT_VERSION_CONFLICT"
    assert "更新" in detail["message"]


def test_null_base_version_conflicts_when_draft_exists(client: TestClient, user) -> None:
    """前端本地没有服务端版本号（base_version=null）时不能覆盖已有草稿。"""
    token, _ = user
    _put(client, token, {"content": {"a": 1}, "base_version": 0})
    resp = client.put(ENDPOINT, json={"content": {"b": 2}, "base_version": None},
                      headers=auth_headers(token))
    assert resp.status_code == 409


def test_first_save_ignores_base_version(client: TestClient, user) -> None:
    """mock 行为：库里没草稿时 base_version 是什么都不影响，直接建 v1。"""
    token, _ = user
    body = _put(client, token, {"content": {"a": 1}, "base_version": 999})
    assert body["version"] == 1


def test_content_must_be_object(client: TestClient, user) -> None:
    token, _ = user
    resp = client.put(ENDPOINT, json={"content": "字符串草稿", "base_version": 0},
                      headers=auth_headers(token))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_oversize_rejected_and_boundary_passes(client: TestClient, db, user) -> None:
    token, _ = user
    from app.core.config import settings

    limit = settings.draft_max_bytes
    # 正好压线：json.dumps 后字节数 <= limit
    pad = limit - len(json.dumps({"k": ""}, ensure_ascii=False).encode("utf-8"))
    ok = _put(client, token, {"content": {"k": "a" * pad}, "base_version": 0})
    assert ok["version"] == 1

    resp = client.put(ENDPOINT, json={"content": {"k": "a" * (pad + 1)}, "base_version": 1},
                      headers=auth_headers(token))
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "256" in detail["message"] or "KB" in detail["message"]


def test_delete_then_recreate(client: TestClient, user) -> None:
    token, _ = user
    _put(client, token, {"content": {"a": 1}, "base_version": 0})
    assert client.delete(ENDPOINT, headers=auth_headers(token)).status_code == 204
    assert client.get(ENDPOINT, headers=auth_headers(token)).status_code == 204
    # 删完再存，版本从 1 重新计（旧草稿已不存在，不是 v2）
    body = _put(client, token, {"content": {"b": 2}, "base_version": 0})
    assert body["version"] == 1


def test_user_isolation(client: TestClient, user) -> None:
    token, _ = user
    _put(client, token, {"content": {"owner": "a"}, "base_version": 0})

    other = register_user(client, username="隔壁同学")
    other_token = other["access_token"]
    resp = client.get(ENDPOINT, headers=auth_headers(other_token))
    assert resp.status_code == 204  # 看不到别人的草稿
    body = _put(client, other_token, {"content": {"owner": "b"}, "base_version": 0})
    assert body["content"] == {"owner": "b"}  # 各存各的，互不冲突


@pytest.mark.parametrize("method, body", [("get", None), ("put", {}), ("delete", None)])
def test_requires_auth(client: TestClient, method: str, body: dict | None) -> None:
    call = getattr(client, method)
    resp = call(ENDPOINT, json=body) if method == "put" else call(ENDPOINT)
    assert resp.status_code == 401
