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


def _check_https_url(value: str, *, hosts: frozenset[str], label: str) -> str:
    """https + 无凭据/查询串/片段 + 443 + 白名单 host；两个 provider 共用一条路径。"""
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ApiError(ErrorCode.VALIDATION_ERROR, f"{label} 必须是 https", 400)
    if parsed.username or parsed.password:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, f"{label} 不能带账号密码", 400
        )
    if parsed.query or parsed.fragment:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, f"{label} 不能带查询串或片段", 400
        )
    try:
        port = parsed.port
    except ValueError:
        # urlparse().port 在端口越界/非数字时抛 ValueError（不是返回 None），
        # 不接住就会一路变成 500 INTERNAL_ERROR
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, f"{label} 端口不合法", 400
        ) from None
    if port not in (None, 443):
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, f"{label} 只允许 443 端口", 400
        )
    if parsed.hostname not in hosts:
        allowed = " / ".join(sorted(hosts))
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, f"{label} 的域名不在白名单（{allowed}）", 400
        )
    return value.rstrip("/")


def _normalize_base_url(provider: str, base_url: str | None) -> str | None:
    value = (base_url or "").strip()
    if provider == "deepseek":
        if not value:
            return None  # 走系统默认 https://api.deepseek.com
        return _check_https_url(
            value, hosts=frozenset({"api.deepseek.com"}), label="deepseek 的 base_url"
        )

    if not value:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, "openai_compatible 需要 base_url", 400
        )
    return _check_https_url(
        value, hosts=ALLOWED_BASE_URL_HOSTS, label="base_url"
    )


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
    api_key = (data.api_key or "").strip()
    row = session.get(UserAiSettings, user_id)
    if row is None and not api_key:
        raise ApiError(ErrorCode.VALIDATION_ERROR, "首次配置必须填 api_key", 400)

    ciphertext = None
    if api_key:
        try:
            ciphertext = encrypt_secret(api_key)
        except SettingsCryptoError as exc:
            # 服务端没配加密密钥：这不是用户的输入问题，不能报 400
            raise ApiError(ErrorCode.AI_PROVIDER_ERROR, str(exc), 503) from None

    if row is None:
        row = UserAiSettings(user_id=user_id)
        session.add(row)
    row.provider = data.provider
    row.base_url = base_url
    row.model = data.model.strip()
    if ciphertext is not None:
        # 省略 api_key = 保留原 Key（只改 model/base_url 时不必重粘）
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
