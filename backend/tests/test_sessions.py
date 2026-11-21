"""BE-028 会话吊销 + BE-029 改密：token_version 只在"全踢"时 +1。

口径（定案单 2026-11-21 §3）：登录**不动**版本（手机+电脑可同时在线）；
登出**不动**版本（只清前端，避免踢掉其他设备）；改密 +1（所有设备重新登录）。
老 token（没有 `ver` 声明）按 0 处理，部署后不会把在线用户集体踢下线。
"""
from __future__ import annotations

from datetime import timedelta

import jwt as pyjwt

from app.core.errors import ErrorCode
from app.db.base import utcnow
from tests.conftest import TEST_SECRET, auth_headers, register_user

PASSWORD = "p@ssw0rd9"
NEW_PASSWORD = "n3w-p@ssw0rd"


def _login(client, username: str, password: str = PASSWORD):
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def _me(client, token: str):
    return client.get("/api/v1/auth/me", headers=auth_headers(token))


def _change(client, token: str, current: str = PASSWORD, new: str = NEW_PASSWORD):
    return client.post(
        "/api/v1/auth/change-password",
        json={"current_password": current, "new_password": new},
        headers=auth_headers(token),
    )


def _legacy_token(user_id: int, *, version: int | None = None) -> str:
    """造一个 BE-028 之前的 token：只有 sub/iat/exp，没有 ver。"""
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=7),
    }
    if version is not None:
        payload["ver"] = version
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def test_login_keeps_other_sessions(client) -> None:
    """手机拍题 + 电脑做题：后登录的不许把先登录的踢下线。"""
    first = register_user(client)["access_token"]
    assert _me(client, first).status_code == 200

    second = _login(client, "小明_01").json()["access_token"]
    assert _me(client, first).status_code == 200
    assert _me(client, second).status_code == 200


def test_logout_does_not_invalidate_token(client) -> None:
    """登出只清前端：服务端不吊销，否则手机上退出会把电脑一起踢下线。"""
    token = register_user(client)["access_token"]

    resp = client.post("/api/v1/auth/logout", headers=auth_headers(token))
    assert resp.status_code == 204, resp.text
    assert _me(client, token).status_code == 200

    # 重新登录也不影响已有会话
    fresh = _login(client, "小明_01")
    assert fresh.status_code == 200
    assert _me(client, token).status_code == 200


def test_logout_requires_auth(client) -> None:
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)


def test_change_password_revokes_all_tokens(client) -> None:
    token = register_user(client)["access_token"]

    resp = _change(client, token)
    assert resp.status_code == 204, resp.text

    # 当前设备的旧 token 也失效；旧密码不能再登录，新密码可以
    stale = _me(client, token)
    assert stale.status_code == 401
    assert stale.json()["detail"]["code"] == str(ErrorCode.AUTH_TOKEN_EXPIRED)
    assert _login(client, "小明_01").status_code == 401
    fresh = _login(client, "小明_01", NEW_PASSWORD)
    assert fresh.status_code == 200
    assert _me(client, fresh.json()["access_token"]).status_code == 200


def test_change_password_wrong_current_keeps_session(client) -> None:
    token = register_user(client)["access_token"]

    resp = _change(client, token, current="wrong-old-pass")
    assert resp.status_code == 401, resp.text
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)
    # 失败不能把当前设备踢掉，也不能改动密码
    assert _me(client, token).status_code == 200
    assert _login(client, "小明_01").status_code == 200


def test_change_password_rejects_same_password(client) -> None:
    token = register_user(client)["access_token"]

    resp = _change(client, token, current=PASSWORD, new=PASSWORD)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == str(ErrorCode.VALIDATION_ERROR)
    assert _me(client, token).status_code == 200


def test_change_password_validates_new_password(client) -> None:
    token = register_user(client)["access_token"]

    # 少于 8 位 → 请求校验失败（400，不是 500/422）
    assert _change(client, token, new="short").status_code == 400
    # 超过 bcrypt 的 72 字节 → 同样在入口拒掉
    long_password = "密" * 30  # 90 字节
    assert _change(client, token, new=long_password).status_code == 400
    assert _me(client, token).status_code == 200


def test_change_password_is_rate_limited(client) -> None:
    token = register_user(client)["access_token"]
    for _ in range(5):
        assert _change(client, token, current="wrong-old-pass").status_code == 401

    blocked = _change(client, token)
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["detail"]["code"] == str(ErrorCode.AUTH_RATE_LIMITED)


def test_legacy_token_without_ver_is_accepted_until_password_change(client) -> None:
    body = register_user(client)
    user_id = body["user"]["id"]

    legacy = _legacy_token(user_id)
    assert _me(client, legacy).status_code == 200

    # 改密把版本推到 1，没有 ver 的老 token 随即失效
    assert _change(client, body["access_token"]).status_code == 204
    stale = _me(client, legacy)
    assert stale.status_code == 401
    assert stale.json()["detail"]["code"] == str(ErrorCode.AUTH_TOKEN_EXPIRED)


def test_token_with_wrong_version_is_rejected(client) -> None:
    body = register_user(client)
    token = body["access_token"]
    user_id = body["user"]["id"]

    assert _change(client, token).status_code == 204
    forged = _legacy_token(user_id, version=0)
    assert _me(client, forged).status_code == 401


def test_non_integer_ver_is_rejected(client) -> None:
    body = register_user(client)
    now = utcnow()
    bad = pyjwt.encode(
        {"sub": str(body["user"]["id"]), "ver": "abc", "iat": now, "exp": now + timedelta(days=1)},
        TEST_SECRET,
        algorithm="HS256",
    )
    resp = _me(client, bad)
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)


def test_change_password_does_not_affect_other_users(client) -> None:
    mine = register_user(client)["access_token"]
    other = register_user(client, username="小红_02")["access_token"]

    assert _change(client, mine).status_code == 204
    assert _me(client, mine).status_code == 401
    assert _me(client, other).status_code == 200


def test_bump_token_version_reads_value_inside_transaction(client, db) -> None:
    """版本必须在同一事务里用当前读拿回（MySQL RR 下普通 SELECT 会读快照旧值）。"""
    from app.models import User
    from app.services import auth_service

    user_id = register_user(client)["user"]["id"]
    with db() as first:
        v1 = auth_service._bump_token_version(first, user_id)
        first.commit()
    with db() as second:
        v2 = auth_service._bump_token_version(second, user_id)
        second.commit()

    assert (v1, v2) == (1, 2)
    with db() as session:
        assert session.get(User, user_id).token_version == 2
