"""认证三端点 + JWT + 限流的测试（BE-003 验收项）。

覆盖：注册/重名 409/参数校验 400、登录成败与 401 形状、
过期与伪造 token、未带 token、/auth/me 归属，以及 5 次/分钟/IP 限流。
fixture 在 tests/conftest.py。
"""
from __future__ import annotations

import time
from datetime import timedelta

import jwt as pyjwt
import pytest

from app.core.errors import ApiError, ErrorCode
from app.core.security import PASSWORD_MAX_BYTES, verify_password
from app.db.base import utcnow
from app.models import User
from app.services.auth_service import LoginRateLimiter
from tests.conftest import TEST_SECRET, auth_headers, register_user


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


def test_rate_limit_window_expires() -> None:
    """滑动窗口滑过之后重新放行（计数与过期清理由 limits 负责）。"""
    limiter = LoginRateLimiter(limit=1, window_s=1)
    limiter.record_failure("198.51.100.7")
    with pytest.raises(ApiError) as excinfo:
        limiter.check("198.51.100.7")
    assert excinfo.value.code == ErrorCode.AUTH_RATE_LIMITED

    time.sleep(1.05)
    limiter.check("198.51.100.7")  # 窗口滑过，不抛


def test_limit_identifiers_have_business_namespace(client, monkeypatch) -> None:
    """登录/注册的桶要带业务前缀：两个限流器配成同一额度时，
    Redis 多实例共用存储也不会串桶。"""
    from app.core.rate_limit import SlidingWindowLimiter

    seen: list[tuple[str, tuple[str, ...]]] = []
    for method in ("check", "record", "hit"):
        original = getattr(SlidingWindowLimiter, method)

        def make_spy(name, orig):
            def spy(self, *identifiers):
                seen.append((name, identifiers))
                return orig(self, *identifiers)

            return spy

        monkeypatch.setattr(SlidingWindowLimiter, method, make_spy(method, original))

    data = _register(client, "namespace_01")
    client.post(
        "/api/v1/auth/login", json={"username": "namespace_01", "password": "wrong-pass-1"}
    )
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong-pass-1", "new_password": "new-p@ssw0rd9"},
        headers=auth_headers(data["access_token"]),
    )

    namespaced = {(method, identifiers[0]) for method, identifiers in seen if identifiers}
    assert ("hit", "register") in namespaced, "注册要带 register 前缀"
    assert ("check", "login") in namespaced, "登录要带 login 前缀"
    assert ("record", "login") in namespaced, "登录失败计数也要带 login 前缀"
    assert ("check", "change-password") in namespaced, "改密要带 change-password 前缀"
    assert ("record", "change-password") in namespaced, "改密失败计数也要带 change-password 前缀"


def test_rate_limit_config_rejects_non_positive(monkeypatch) -> None:
    """limits.parse 对 0 静默放过（0 窗口变 1 秒、0 额度永远 429），启动期要自己拒。"""
    from app.core import rate_limit
    from app.core.config import settings

    monkeypatch.setattr(settings, "register_rate_limit", 0)
    with pytest.raises(ValueError, match="REGISTER_RATE_LIMIT"):
        rate_limit.validate_rate_limit_config()

    monkeypatch.setattr(settings, "register_rate_limit", 30)
    monkeypatch.setattr(settings, "login_rate_window_s", 0)
    with pytest.raises(ValueError, match="LOGIN_RATE_LIMIT"):
        rate_limit.validate_rate_limit_config()


def test_password_is_hashed_not_stored_plaintext(client, db) -> None:
    _register(client, "alice")
    with db() as s:
        user = s.query(User).filter(User.username == "alice").one()
    assert user.password_hash.startswith("$2")
    assert "p@ssw0rd9" != user.password_hash
    # 散列验证能通过，登录链路用的就是库里这份值
    assert verify_password("p@ssw0rd9", user.password_hash)


def test_register_is_rate_limited_per_ip(client, monkeypatch) -> None:
    """注册按 IP 限额：反复注册是"换号绕过按用户额度"的入口。"""
    from limits import parse

    from app.services.auth_service import register_limiter

    # 默认 30/小时是为了容纳实验室同 NAT 的全班注册；这里把额度压小来测判据
    monkeypatch.setattr(register_limiter, "item", parse("2/hour"))
    for index in range(2):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": f"ratelimit_{index}", "password": "p@ssw0rd9"},
        )
        assert resp.status_code == 200, resp.text

    blocked = client.post(
        "/api/v1/auth/register",
        json={"username": "ratelimit_2", "password": "p@ssw0rd9"},
    )
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["detail"]["code"] == str(ErrorCode.AUTH_RATE_LIMITED)


def test_duplicate_username_does_not_consume_register_quota(client, monkeypatch) -> None:
    """重名 409 不扣额度：同 NAT 下一个人打错用户名，不该吃掉全班的名额。"""
    from limits import parse

    from app.services.auth_service import register_limiter

    monkeypatch.setattr(register_limiter, "item", parse("2/hour"))
    payload = {"username": "alice", "password": "p@ssw0rd9"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200

    for _ in range(2):
        dup = client.post("/api/v1/auth/register", json=payload)
        assert dup.status_code == 409, dup.text

    # 还剩一个名额：若重名也计数，这里已经被 429 挡住了
    rest = client.post(
        "/api/v1/auth/register",
        json={"username": "bob", "password": "p@ssw0rd9"},
    )
    assert rest.status_code == 200, rest.text

    blocked = client.post(
        "/api/v1/auth/register",
        json={"username": "carol", "password": "p@ssw0rd9"},
    )
    assert blocked.status_code == 429, blocked.text
