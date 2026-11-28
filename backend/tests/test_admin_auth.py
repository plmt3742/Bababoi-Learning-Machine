"""ADM-002 / ADM-009：管理员登录、require_admin 越权矩阵、审计、seed 脚本。

越权是这次明确要盯的点：学生 token 访问 /admin/* 必须 403，禁用/降级后旧 token
也必须立刻失效——角色只信 DB，不信签发时的状态。
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app.core.config import settings
from app.core.security import decode_access_token, hash_password
from app.db.base import Base
from app.models import AdminAuditLog, User
from tests.conftest import auth_headers, register_user

ADMIN_PASSWORD = "Adm1n-pass!"
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _create_user(db, username: str, password: str, **fields) -> int:
    session = db()
    try:
        user = User(
            username=username,
            password_hash=hash_password(password),
            **fields,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id
    finally:
        session.close()


def _admin_login(client: TestClient, username: str = "admin01", password: str = ADMIN_PASSWORD):
    return client.post(
        "/api/v1/admin/auth/login",
        json={"username": username, "password": password},
    )


# --- 登录边界 -------------------------------------------------------------


def test_student_cannot_login_to_admin(client, db):
    register_user(client, username="student01")
    resp = _admin_login(client, "student01", "p@ssw0rd9")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ADMIN_REQUIRED"


def test_admin_login_wrong_password_is_401_without_revealing_role(client, db):
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    resp = _admin_login(client, "admin01", "wrong-pass")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"

    resp = _admin_login(client, "nobody", "wrong-pass")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_admin_login_returns_profile_and_writes_audit(client, db):
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin", email="a@example.com")

    resp = _admin_login(client)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": body["user"]["id"],
        "username": "admin01",
        "email": "a@example.com",
        "role": "admin",
        "must_change_password": False,
    }

    with db() as session:
        logs = session.scalars(select(AdminAuditLog)).all()
        assert [(log.action, log.actor_username, log.result) for log in logs] == [
            ("admin.login", "admin01", "success")
        ]
        assert logs[0].ip  # 来源落库，后续排障用
        assert logs[0].request_id


def test_admin_token_uses_shorter_ttl(client, db):
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["exp"] - payload["iat"] == settings.admin_token_expire_hours * 3600
    assert settings.admin_token_expire_hours == 8


# --- require_admin 越权矩阵 -------------------------------------------------


def test_admin_endpoints_reject_missing_and_student_tokens(client, db):
    assert client.get("/api/v1/admin/me").status_code == 401

    student = register_user(client, username="student01")
    resp = client.get("/api/v1/admin/me", headers=auth_headers(student["access_token"]))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ADMIN_REQUIRED"

    resp = client.post(
        "/api/v1/admin/logout", headers=auth_headers(student["access_token"])
    )
    assert resp.status_code == 403


def test_admin_me_and_logout_work_and_logout_is_audited(client, db):
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]
    headers = auth_headers(token)

    me = client.get("/api/v1/admin/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    logout = client.post("/api/v1/admin/logout", headers=headers)
    assert logout.status_code == 204

    with db() as session:
        actions = session.scalars(
            select(AdminAuditLog.action).order_by(AdminAuditLog.id)
        ).all()
    assert actions == ["admin.login", "admin.logout"]


def test_disabled_admin_token_is_rejected_after_login(client, db):
    admin_id = _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]

    # 禁用发生在签发之后：旧 token 仍带着有效签名，但每次请求查 DB 必须拦住
    session = db()
    try:
        session.get(User, admin_id).disabled_at = datetime(2026, 11, 28, 12, 0, 0)
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/v1/admin/me", headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_DISABLED"

    # 禁用后重新登录同样拒绝（密码正确也不行）
    resp = _admin_login(client)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_role_downgrade_takes_effect_without_reissue(client, db):
    admin_id = _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]

    session = db()
    try:
        session.get(User, admin_id).role = "student"
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/v1/admin/me", headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ADMIN_REQUIRED"


def test_force_logout_invalidates_old_admin_token(client, db):
    admin_id = _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]

    session = db()
    try:
        session.get(User, admin_id).token_version += 1
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/v1/admin/me", headers=auth_headers(token))
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_TOKEN_EXPIRED"


# --- 学生端受影响的边界 ------------------------------------------------------


def test_register_never_creates_admin(client, db):
    body = register_user(client, username="student02")
    assert body["user"]["username"] == "student02"

    with db() as session:
        roles = session.scalars(select(User.role)).all()
    assert roles == ["student"]


def test_disabled_student_cannot_login_or_use_old_token(client, db):
    student_id = _create_user(db, "student01", "p@ssw0rd9")
    token = client.post(
        "/api/v1/auth/login",
        json={"username": "student01", "password": "p@ssw0rd9"},
    ).json()["access_token"]

    session = db()
    try:
        session.get(User, student_id).disabled_at = datetime(2026, 11, 28, 12, 0, 0)
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_DISABLED"

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "student01", "password": "p@ssw0rd9"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_token_payload_does_not_carry_role(client, db):
    """角色不进 JWT：否则降级后 7 天内旧 token 仍是 admin。"""
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert "role" not in payload
    assert decode_access_token(token)[0]  # 签名与 ver 解析正常


def test_admin_login_failures_do_not_lock_student_login(client, db):
    """复核单 §3：admin 与学生登录必须各用各的限流桶。"""
    register_user(client, username="student01")
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")

    for _ in range(settings.login_rate_limit):
        assert _admin_login(client, "admin01", "wrong-pass").status_code == 401
    assert _admin_login(client, "admin01", "wrong-pass").status_code == 429

    ok = client.post(
        "/api/v1/auth/login",
        json={"username": "student01", "password": "p@ssw0rd9"},
    )
    assert ok.status_code == 200, ok.text


def test_student_login_failures_do_not_lock_admin_login(client, db):
    register_user(client, username="student01")
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")

    for _ in range(settings.login_rate_limit):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "student01", "password": "wrong-pass"},
        )
        assert resp.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "student01", "password": "wrong-pass"},
        ).status_code
        == 429
    )

    assert _admin_login(client).status_code == 200


def test_admin_logout_revokes_own_tokens_only(client, db):
    """11-28 定案 B：管理端登出必须吊销 token，但不能波及学生/其他管理员。"""
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    _create_user(db, "admin02", ADMIN_PASSWORD, role="admin")
    token_a = _admin_login(client).json()["access_token"]  # 设备 1
    token_b = _admin_login(client).json()["access_token"]  # 设备 2
    token_other = _admin_login(client, "admin02").json()["access_token"]
    student = register_user(client, username="student01")

    resp = client.post("/api/v1/admin/logout", headers=auth_headers(token_a))
    assert resp.status_code == 204

    for token in (token_a, token_b):
        resp = client.get("/api/v1/admin/me", headers=auth_headers(token))
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_TOKEN_EXPIRED"

    assert (
        client.get("/api/v1/admin/me", headers=auth_headers(token_other)).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers=auth_headers(student["access_token"])
        ).status_code
        == 200
    )


def test_admin_logout_revokes_even_when_audit_write_fails(client, db, monkeypatch):
    """bump 必须独立 commit：审计打桩抛异常后 token 仍要失效（复核单 §11.1 坑 1）。"""
    _create_user(db, "admin01", ADMIN_PASSWORD, role="admin")
    token = _admin_login(client).json()["access_token"]

    from app.services import audit_service

    def boom(*_args, **_kwargs):
        raise RuntimeError("audit down")

    monkeypatch.setattr(audit_service, "record", boom)

    resp = client.post("/api/v1/admin/logout", headers=auth_headers(token))
    assert resp.status_code == 204

    resp = client.get("/api/v1/admin/me", headers=auth_headers(token))
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_TOKEN_EXPIRED"


# --- seed 脚本 --------------------------------------------------------------


def _seed_env(db_path: Path, **overrides) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ADMIN_USERNAME", None)
    env.pop("ADMIN_PASSWORD", None)
    env.pop("ADMIN_EMAIL", None)
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
            "APP_ENV": "development",
            "ADMIN_USERNAME": "admin01",
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
            "ADMIN_EMAIL": "admin@example.com",
        }
    )
    env.update(overrides)
    return env


def _run_seed(env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/seed_admin.py", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _migrated_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "seed.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(engine)
    engine.dispose()
    return db_path


def test_seed_admin_requires_password(tmp_path):
    db_path = _migrated_db(tmp_path)
    env = _seed_env(db_path, ADMIN_PASSWORD="")
    result = _run_seed(env)
    assert result.returncode == 2
    assert "ADMIN_PASSWORD" in result.stderr
    assert sqlite3.connect(db_path).execute("select count(*) from users").fetchone()[0] == 0


def test_seed_admin_creates_admin_and_only_resets_on_flag(tmp_path):
    db_path = _migrated_db(tmp_path)
    env = _seed_env(db_path)

    result = _run_seed(env)
    assert result.returncode == 0, result.stderr
    assert ADMIN_PASSWORD not in result.stdout  # 口令绝不回显

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "select username, role, email from users where username='admin01'"
    ).fetchone()
    assert row == ("admin01", "admin", "admin@example.com")
    original_hash = conn.execute(
        "select password_hash from users where username='admin01'"
    ).fetchone()[0]

    # 不带 --reset 重跑：只确认 role，不碰密码
    result = _run_seed(env)
    assert result.returncode == 0, result.stderr
    assert (
        conn.execute("select password_hash from users where username='admin01'").fetchone()[0]
        == original_hash
    )

    # --reset 才重写密码
    result = _run_seed(env, "--reset", "--yes")
    assert result.returncode == 0, result.stderr
    new_hash = conn.execute(
        "select password_hash from users where username='admin01'"
    ).fetchone()[0]
    conn.close()

    from app.core.security import verify_password

    assert new_hash != original_hash
    assert verify_password(ADMIN_PASSWORD, new_hash)
    assert not verify_password("another-pass", new_hash)


def test_seed_admin_promotes_existing_student(tmp_path):
    db_path = _migrated_db(tmp_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "insert into users (username, password_hash, role, must_change_password,"
        " enforce_same_question_type, token_version, created_at, updated_at)"
        " values ('student01', 'x', 'student', 0, 1, 0,"
        " '2026-11-01 00:00:00', '2026-11-01 00:00:00')"
    )
    conn.commit()
    conn.close()

    env = _seed_env(db_path, ADMIN_USERNAME="student01")
    result = _run_seed(env)
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(db_path)
    assert conn.execute(
        "select role from users where username='student01'"
    ).fetchone()[0] == "admin"
    conn.close()


PROD_PASSWORD = "Adm1n-pass!2026"


def test_seed_admin_production_allows_first_create_but_not_silent_reset(tmp_path):
    """复核单 §2：生产切 APP_ENV=production 后必须还有正规建号路径。"""
    db_path = _migrated_db(tmp_path)
    env = _seed_env(db_path, APP_ENV="production", ADMIN_PASSWORD=PROD_PASSWORD)

    created = _run_seed(env)
    assert created.returncode == 0, created.stderr
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "select role, password_hash from users where username='admin01'"
    ).fetchone()
    assert row[0] == "admin"
    original_hash = row[1]

    # 已存在：幂等、不碰口令
    again = _run_seed(env)
    assert again.returncode == 0, again.stderr
    assert (
        conn.execute(
            "select password_hash from users where username='admin01'"
        ).fetchone()[0]
        == original_hash
    )

    # --reset 缺 --yes：拒绝且不改库
    refused = _run_seed(env, "--reset")
    assert refused.returncode == 2
    assert (
        conn.execute(
            "select password_hash from users where username='admin01'"
        ).fetchone()[0]
        == original_hash
    )

    # 服务器 shell 显式 --reset --yes：允许改口令
    reset = _run_seed(env, "--reset", "--yes")
    assert reset.returncode == 0, reset.stderr
    assert (
        conn.execute(
            "select password_hash from users where username='admin01'"
        ).fetchone()[0]
        != original_hash
    )
    conn.close()


def test_seed_admin_production_requires_strong_password(tmp_path):
    db_path = _migrated_db(tmp_path)
    env = _seed_env(db_path, APP_ENV="production", ADMIN_PASSWORD="short123")
    result = _run_seed(env)
    assert result.returncode == 2
    assert "12" in result.stderr
    assert sqlite3.connect(db_path).execute("select count(*) from users").fetchone()[0] == 0
