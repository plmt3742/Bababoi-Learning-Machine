"""解析这次调用该用哪把 Key（ADR-007 / 05 §6.9）。

顺序：用户自己的配置 → 系统 `.env` → 报错。**不静默回退**——用户配了 Key 还悄悄
走系统 Key，会让人以为自己的额度生效了，排查时也没有任何线索；`ai_call_logs.key_source`
就是为了让这件事有据可查。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import sessionmaker

from app.ai.errors import AIProviderError
from app.core.config import settings
from app.core.crypto import SettingsCryptoError, decrypt_secret
from app.models import UserAiSettings


@dataclass(frozen=True)
class LLMConfig:
    # repr=False：ADR-007 的硬约束是任何日志/错误体不得包含原始 Key，
    # 而 dataclass 默认 repr 会把明文带进 logger.debug(cfg) 或异常信息里
    api_key: str = field(repr=False)
    base_url: str
    model: str
    key_source: str  # user | system
    user_id: int | None = None


def system_config() -> LLMConfig:
    return LLMConfig(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        key_source="system",
    )


def model_hint(session_factory: sessionmaker | None, user_id: int | None) -> str:
    """用户配置的 model（只读、不解密），没有就用系统 model。

    给识图缓存键用：BYOK 换了模型必须不命中，但命中缓存不该因此要求 Key。
    """
    if session_factory is None or user_id is None:
        return settings.llm_model
    with session_factory() as session:
        row = session.get(UserAiSettings, user_id)
    return (row.model if row is not None and row.model else settings.llm_model)


def resolve_llm_config(session_factory: sessionmaker, user_id: int) -> LLMConfig:
    with session_factory() as session:
        row = session.get(UserAiSettings, user_id)

    if row is not None:
        try:
            api_key = decrypt_secret(row.api_key_ciphertext)
        except SettingsCryptoError as exc:
            raise AIProviderError(str(exc)) from None
        return LLMConfig(
            api_key=api_key,
            base_url=row.base_url or settings.llm_base_url,
            model=row.model or settings.llm_model,
            key_source="user",
            user_id=user_id,
        )

    if not settings.llm_api_key:
        raise AIProviderError("未配置 AI Key（用户与系统都没有）")
    return system_config()
