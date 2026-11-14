"""BYOK 的读写与校验（ADR-007 / 05 §6.9）。

三条边界：
- 只返回掩码，明文 Key 不出响应、不进日志、不进 DB；
- `base_url` 先收窄到 `https` + 白名单 host，SSRF 面等以后要做自定义地址时再展开；
- 加密密钥缺失时明确 503，而不是静默退回系统 Key（那会让用户以为自己的 Key 生效了）。
"""
from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.crypto import SettingsCryptoError, encrypt_secret
from app.core.errors import ApiError, ErrorCode
from app.models import UserAiSettings
from app.schemas.settings import AiSettingsOut, AiSettingsUpdate

# ADR-007 §2.1：至少这两个；自定义 host 要先做内网/回环/metadata 防护再放开
ALLOWED_BASE_URL_HOSTS = frozenset({"api.deepseek.com", "api.openai.com"})


def mask_key(api_key: str) -> str:
    last4 = api_key[-4:]
    return f"sk-****{last4}" if api_key.startswith("sk-") else f"****{last4}"


def _normalize_base_url(provider: str, base_url: str | None) -> str | None:
    value = (base_url or "").strip()
    if provider == "deepseek":
        if not value:
            return None  # 走系统默认 https://api.deepseek.com
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != "api.deepseek.com":
            raise ApiError(
                ErrorCode.VALIDATION_ERROR,
                "deepseek 的 base_url 只能留空或使用 https://api.deepseek.com",
                400,
            )
        return value.rstrip("/")

    if not value:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, "openai_compatible 需要 base_url", 400
        )
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, "base_url 必须是 https", 400
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, "base_url 不能带账号、查询串或片段", 400
        )
    if parsed.port not in (None, 443):
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, "base_url 只允许 443 端口", 400
        )
    if parsed.hostname not in ALLOWED_BASE_URL_HOSTS:
        allowed = " / ".join(sorted(ALLOWED_BASE_URL_HOSTS))
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"base_url 的域名不在白名单（{allowed}）",
            400,
        )
    return value.rstrip("/")


def _to_out(row: UserAiSettings | None) -> AiSettingsOut:
    if row is None:
        return AiSettingsOut(configured=False)
    return AiSettingsOut(
        configured=True,
        provider=row.provider,
        base_url=row.base_url,
        model=row.model,
        api_key_masked=(
            f"sk-****{row.key_last4}" if row.provider == "deepseek" else f"****{row.key_last4}"
        ),
        updated_at=row.updated_at,
    )


def get_settings(session: Session, user_id: int) -> AiSettingsOut:
    return _to_out(session.get(UserAiSettings, user_id))


def save_settings(
    session: Session, user_id: int, data: AiSettingsUpdate
) -> AiSettingsOut:
    base_url = _normalize_base_url(data.provider, data.base_url)
    api_key = data.api_key.strip()
    if len(api_key) < 8:
        raise ApiError(ErrorCode.VALIDATION_ERROR, "api_key 至少 8 位", 400)

    try:
        ciphertext = encrypt_secret(api_key)
    except SettingsCryptoError as exc:
        # 服务端没配加密密钥：这不是用户的输入问题，不能报 400
        raise ApiError(ErrorCode.AI_PROVIDER_ERROR, str(exc), 503) from None

    row = session.get(UserAiSettings, user_id)
    if row is None:
        row = UserAiSettings(user_id=user_id)
        session.add(row)
    row.provider = data.provider
    row.base_url = base_url
    row.model = data.model.strip()
    row.api_key_ciphertext = ciphertext
    row.key_last4 = api_key[-4:]
    session.commit()
    session.refresh(row)
    return _to_out(row)


def delete_settings(session: Session, user_id: int) -> None:
    row = session.get(UserAiSettings, user_id)
    if row is not None:
        session.delete(row)
        session.commit()
