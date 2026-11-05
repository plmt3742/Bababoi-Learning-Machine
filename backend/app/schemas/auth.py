"""认证相关的请求/响应结构（05 §6.3）。

用户名/密码的位数与字符集是写死的契约值，不是可调参数，所以不放 config.py。
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 8

# 字母/数字/下划线/中文（05 §6.3）。不用 \w：它会放行日文假名等超出契约的字符
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff]+$")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=USERNAME_MIN, max_length=USERNAME_MAX)
    password: str = Field(min_length=PASSWORD_MIN, max_length=128)
    email: str | None = Field(default=None, max_length=128)

    @field_validator("username")
    @classmethod
    def username_charset(cls, value: str) -> str:
        if not _USERNAME_PATTERN.fullmatch(value):
            raise ValueError("用户名只能包含字母、数字、下划线、中文")
        return value

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, value: str) -> str:
        # bcrypt 只取前 72 字节，见 core/security.py 的说明
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码过长（最多 72 字节）")
        return value

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str | None) -> str | None:
        # O-03：email 只是可选字段，做个最轻的存在性检查就够，MVP 不做真实验证
        if value is not None and "@" not in value:
            raise ValueError("email 格式不正确")
        return value


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    """/auth/me 与登录响应里嵌的用户信息。密码散列绝不进这里。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
