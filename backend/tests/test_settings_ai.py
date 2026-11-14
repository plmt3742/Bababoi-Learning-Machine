"""BYOK（BE-020 / ADR-007）：接口边界 + Key 解析顺序 + 日志来源。"""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.ai.client import _client_cache, build_llm_client
from app.ai.errors import AIProviderError
from app.ai.llm_config import LLMConfig, resolve_llm_config
from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.models import AiCallLog, UserAiSettings
from app.services import ai_log
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def enc_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "settings_encryption_key", key)
    return key


@pytest.fixture(autouse=True)
def _clear_client_cache():
    _client_cache.clear()
    yield
    _client_cache.clear()


def _put(client, token, body):
    return client.put("/api/v1/settings/ai", json=body, headers=auth_headers(token))


def _get(client, token):
    return client.get("/api/v1/settings/ai", headers=auth_headers(token))


def _delete(client, token):
    return client.delete("/api/v1/settings/ai", headers=auth_headers(token))


def test_default_is_unconfigured(client, db) -> None:
    token = register_user(client)["access_token"]
    resp = _get(client, token)
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["api_key_masked"] is None and body["updated_at"] is None


def test_put_masks_and_encrypts(client, db, enc_key) -> None:
    token = register_user(client)["access_token"]
    secret = "sk-test-1234567890"
    resp = _put(
        client,
        token,
        {"provider": "deepseek", "model": "deepseek-flash", "api_key": secret},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["configured"] is True
    assert body["api_key_masked"] == "sk-****7890"
    assert secret not in resp.text, "原始 Key 不能出现在响应里"

    with db() as session:
        row = session.scalar(select(UserAiSettings))
        assert row is not None
        assert row.key_last4 == "7890"
        assert row.api_key_ciphertext != secret
        assert secret not in row.api_key_ciphertext
        assert decrypt_secret(row.api_key_ciphertext) == secret


def test_openai_compatible_base_url_whitelist(client, db, enc_key) -> None:
    token = register_user(client)["access_token"]
    ok = _put(
        client,
        token,
        {
            "provider": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "sk-test-123456",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["base_url"] == "https://api.openai.com/v1"

    for base_url in ("http://api.openai.com/v1", "https://evil.example.com/v1"):
        bad = _put(
            client,
            token,
            {
                "provider": "openai_compatible",
                "base_url": base_url,
                "model": "gpt-4o-mini",
                "api_key": "sk-test-123456",
            },
        )
        assert bad.status_code == 400, (base_url, bad.text)
        assert bad.json()["detail"]["code"] == "VALIDATION_ERROR"

    missing = _put(
        client,
        token,
        {"provider": "openai_compatible", "model": "gpt-4o-mini", "api_key": "sk-test-123456"},
    )
    assert missing.status_code == 400


def test_short_key_rejected_and_delete_is_idempotent(client, db, enc_key) -> None:
    token = register_user(client)["access_token"]
    short = _put(client, token, {"provider": "deepseek", "model": "deepseek-flash", "api_key": "short"})
    assert short.status_code == 400
    assert short.json()["detail"]["code"] == "VALIDATION_ERROR"

    assert _delete(client, token).status_code == 204
    assert _delete(client, token).status_code == 204
    assert _get(client, token).json()["configured"] is False


def test_missing_encryption_key_is_503(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "settings_encryption_key", "")
    token = register_user(client)["access_token"]
    resp = _put(
        client,
        token,
        {"provider": "deepseek", "model": "deepseek-flash", "api_key": "sk-test-123456"},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "AI_PROVIDER_ERROR"


def test_settings_are_isolated_per_user(client, db, enc_key) -> None:
    a = register_user(client, username="byokA")["access_token"]
    b = register_user(client, username="byokB")["access_token"]
    assert _put(
        client, a, {"provider": "deepseek", "model": "deepseek-flash", "api_key": "sk-test-123456"}
    ).status_code == 200
    assert _get(client, b).json()["configured"] is False


def test_resolve_prefers_user_key_then_system(client, db, enc_key, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_mock", False)
    monkeypatch.setattr(settings, "llm_api_key", "system-key-1234")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(settings, "llm_model", "deepseek-flash")
    data = register_user(client)
    token, user_id = data["access_token"], data["user"]["id"]

    system_cfg = resolve_llm_config(db, user_id)
    assert system_cfg.key_source == "system"
    assert system_cfg.api_key == "system-key-1234"

    _put(
        client,
        token,
        {"provider": "deepseek", "model": "deepseek-flash", "api_key": "sk-user-123456"},
    )
    user_cfg = resolve_llm_config(db, user_id)
    assert user_cfg.key_source == "user"
    assert user_cfg.api_key == "sk-user-123456"
    assert user_cfg.user_id == user_id

    assert _delete(client, token).status_code == 204
    assert resolve_llm_config(db, user_id).key_source == "system"


def test_no_key_anywhere_raises(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_mock", False)
    monkeypatch.setattr(settings, "llm_api_key", "")
    user_id = register_user(client)["user"]["id"]
    with pytest.raises(AIProviderError):
        resolve_llm_config(db, user_id)


def test_client_cache_hits_same_key_and_marks_source(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_mock", False)
    cfg_a = LLMConfig("sk-a-123456", "https://api.deepseek.com", "deepseek-flash", "user", 1)
    cfg_b = LLMConfig("sk-b-123456", "https://api.deepseek.com", "deepseek-flash", "user", 2)
    client_a = build_llm_client(cfg_a)
    assert build_llm_client(cfg_a) is client_a, "同一把 Key 应复用连接池"
    client_b = build_llm_client(cfg_b)
    assert client_b is not client_a
    assert client_a.key_source == "user" and client_a.user_id == 1


def test_ai_log_records_key_source(client, db, enc_key) -> None:
    user_id = register_user(client)["user"]["id"]
    ai_log.write_call_log(
        db, user_id, "vision", "success", raw_text="{}", key_source="user"
    )
    with db() as session:
        row = session.scalar(select(AiCallLog).order_by(AiCallLog.id.desc()))
        assert row is not None and row.key_source == "user"
