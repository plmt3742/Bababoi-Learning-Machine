"""BE-028 会话吊销：token_version + 登录踢旧会话 + logout。

口径：同一账号同一时刻只有一个会话（新登录让旧 token 立刻失效）；登出同样 +1。
老 token（没有 `ver` 声明）按 0 处理，部署后不会把在线用户集体踢下线。
"""
from __future__ import annotations

from datetime import timedelta

import jwt as pyjwt

from app.core.errors import ErrorCode
from app.db.base import utcnow
from tests.conftest import TEST_SECRET, auth_headers, register_user


def _login(client, username: str, password: str = "p@ssw0rd9"):
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def _me(client, token: str):
    return client.get("/api/v1/auth/me", headers=auth_headers(token))


def _legacy_token(user_id: int) -> str:
    """造一个 BE-028 之前的 token：只有 sub/iat/exp，没有 ver。"""
    now = utcnow()
    return pyjwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(days=7),
        },
        TEST_SECRET,
        algorithm="HS256",
    )


def test_login_kicks_previous_session(client) -> None:
    first = register_user(client)["access_token"]
    assert _me(client, first).status_code == 200

    second = _login(client, "小明_01").json()["access_token"]
    old = _me(client, first)
    assert old.status_code == 401, old.text
    assert old.json()["detail"]["code"] == str(ErrorCode.AUTH_TOKEN_EXPIRED)
    # 新会话不受影响
    assert _me(client, second).status_code == 200


def test_logout_invalidates_current_token(client) -> None:
    token = register_user(client)["access_token"]

    resp = client.post("/api/v1/auth/logout", headers=auth_headers(token))
    assert resp.status_code == 204, resp.text
    assert _me(client, token).status_code == 401

    # 登出后重新登录能拿到有效 token
    fresh = _login(client, "小明_01")
    assert fresh.status_code == 200
    assert _me(client, fresh.json()["access_token"]).status_code == 200


def test_logout_requires_auth(client) -> None:
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)


def test_logout_does_not_affect_other_users(client) -> None:
    mine = register_user(client)["access_token"]
    other = register_user(client, username="小红_02")["access_token"]

    assert client.post("/api/v1/auth/logout", headers=auth_headers(mine)).status_code == 204
    assert _me(client, mine).status_code == 401
    assert _me(client, other).status_code == 200


def test_legacy_token_without_ver_is_accepted_until_next_login(client) -> None:
    body = register_user(client)
    user_id = body["user"]["id"]

    legacy = _legacy_token(user_id)
    assert _me(client, legacy).status_code == 200

    # 登录把版本推到 1，没有 ver 的老 token 随即失效
    assert _login(client, "小明_01").status_code == 200
    stale = _me(client, legacy)
    assert stale.status_code == 401
    assert stale.json()["detail"]["code"] == str(ErrorCode.AUTH_TOKEN_EXPIRED)


def test_token_with_wrong_version_is_rejected(client) -> None:
    body = register_user(client)
    token = body["access_token"]

    # 让版本前进一格，再伪造一个 ver=0 的 token（签名合法、版本过期）
    assert _login(client, "小明_01").status_code == 200
    payload = pyjwt.decode(token, TEST_SECRET, algorithms=["HS256"])
    payload["exp"] = utcnow() + timedelta(days=7)
    payload["ver"] = 0
    forged = pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")
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


def test_bump_token_version_reads_value_inside_transaction(client, db) -> None:
    """版本必须在同一事务里读回；提交后再读会被并发登录推高（前端 review 指出的竞态）。"""
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
