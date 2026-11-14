"""用户 AI Key 的对称加密（ADR-007 / 05 §6.9）。

只存密文 + 分离的 `key_last4`；密钥从 `SETTINGS_ENCRYPTION_KEY` 读（Fernet，32 字节
urlsafe base64）。没有配置密钥时 BYOK 接口返回 503，既有的系统 Key 链路不受影响。
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SettingsCryptoError(RuntimeError):
    """加密密钥缺失/非法，或密文解不开。调用方转成对用户可解释的错误。"""


def _fernet() -> Fernet:
    key = settings.settings_encryption_key
    if not key:
        raise SettingsCryptoError("服务端未配置 SETTINGS_ENCRYPTION_KEY")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise SettingsCryptoError("SETTINGS_ENCRYPTION_KEY 不是合法的 Fernet key") from exc


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise SettingsCryptoError("已保存的 AI Key 无法解密") from exc
