"""认证三端点 + JWT + 限流的测试（BE-003 验收项）。

覆盖：注册/重名 409/参数校验 400、登录成败与 401 形状、
过期与伪造 token、未带 token、/auth/me 归属，以及 5 次/分钟/IP 限流。
fixture 在 tests/conftest.py。
"""
from __future__ import annotations

from datetime import timedelta

import jwt as pyjwt
import pytest

from app.core.errors import ApiError, ErrorCode
from app.core.security import PASSWORD_MAX_BYTES, verify_password
from app.db.base import utcnow
from app.models import User
from app.services.auth_service import LoginRateLimiter
from tests.conftest import TEST_SECRET, register_user


def _register(client, username: str = "小明_01", password: str = "p@ssw0rd9") -> dict:
    return register_user(client, username, password)


def test_register_returns_token_and_user(client) -> None:
    body = _register(client)
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "小明_01"
    assert body["user"]["email"] is None
    assert "password_hash" not in body["user"]
    assert body["user"]["created_at"]


def test_register_rejects_duplicate_username(client) -> None:
    _register(client, "alice")
    resp = client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "p@ssw0rd9"}
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == str(ErrorCode.USERNAME_TAKEN)


def test_register_rejects_bad_username_and_short_password(client) -> None:
    for username in ("ab", "含空格 名", "bad!name", "a" * 33):
        resp = client.post(
            "/api/v1/auth/register", json={"username": username, "password": "p@ssw0rd9"}
        )
        assert resp.status_code == 400, username
        assert resp.json()["detail"]["code"] == str(ErrorCode.VALIDATION_ERROR)

    resp = client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "short7!"}
    )
    assert resp.status_code == 400


def test_register_rejects_over_bcrypt_byte_limit(client) -> None:
    # 24 个中文字符 = 72 字节，再长一位 bcrypt 就会静默截断
    ok = "好" * (PASSWORD_MAX_BYTES // 3)
    too_long = ok + "好"
    assert client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": ok}
    ).status_code == 200
    assert (
        client.post(
            "/api/v1/auth/register", json={"username": "bob", "password": too_long}
        ).status_code
        == 400
    )


def test_login_success_then_me(client) -> None:
    _register(client, "小明_01")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "小明_01", "password": "p@ssw0rd9"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "小明_01"


def test_login_wrong_password_and_unknown_user_same_error(client) -> None:
    _register(client, "alice")
    for payload in (
        {"username": "alice", "password": "wrong-pass-1"},
        {"username": "ghost", "password": "p@ssw0rd9"},
    ):
        resp = client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)


def test_me_requires_token(client) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)


def test_expired_token_returns_dedicated_code(client) -> None:
    expired = pyjwt.encode(
        {
            "sub": "1",
            "iat": utcnow() - timedelta(days=2),
            "exp": utcnow() - timedelta(days=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_TOKEN_EXPIRED)


def test_forged_token_rejected(client) -> None:
    forged = pyjwt.encode(
        {"sub": "1", "exp": utcnow() + timedelta(days=1)},
        "a-wrong-secret-but-long-enough-0123456789abcdef",
        algorithm="HS256",
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == str(ErrorCode.AUTH_INVALID_CREDENTIALS)


def test_users_are_isolated_from_each_other(client) -> None:
    """US-6：每个 token 只能拿到自己的资料（05 §9.4 越权防线的基础）。"""
    first = _register(client, "alice")
    second = _register(client, "bob")
    assert first["user"]["id"] != second["user"]["id"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert me.json()["id"] == second["user"]["id"]
    assert me.json()["username"] == "bob"


def test_login_rate_limit_after_five_failures(client) -> None:
    _register(client, "alice")
    for _ in range(5):
        resp = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "wrong-pass-1"}
        )
        assert resp.status_code == 401

    # 窗口内第 6 次：哪怕密码正确也拒绝（防爆破）
    limited = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "p@ssw0rd9"}
    )
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == str(ErrorCode.AUTH_RATE_LIMITED)


def test_rate_limit_counts_ips_independently() -> None:
    """限流按 IP 隔离：一个 IP 打满不影响另一个（单元级，不起服务）。"""
    limiter = LoginRateLimiter(limit=2, window_s=60)
    for _ in range(2):
        limiter.record_failure("1.1.1.1")
    with pytest.raises(ApiError) as exc:
        limiter.check("1.1.1.1")
    assert exc.value.code == ErrorCode.AUTH_RATE_LIMITED

    limiter.check("2.2.2.2")  # 不抛，即未限流


def test_password_is_hashed_not_stored_plaintext(client, db) -> None:
    _register(client, "alice")
    with db() as s:
        user = s.query(User).filter(User.username == "alice").one()
    assert user.password_hash.startswith("$2")
    assert "p@ssw0rd9" != user.password_hash
    # 散列验证能通过，登录链路用的就是库里这份值
    assert verify_password("p@ssw0rd9", user.password_hash)
