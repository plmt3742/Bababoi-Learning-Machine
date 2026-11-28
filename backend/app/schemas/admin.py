"""管理端请求/响应结构（ADM-002）。

命名刻意与学生端保持一致（snake_case）：`AdminProfile` 是前端 types.ts 里唯一
已是 snake_case 的 DTO，其余 admin 列表 DTO 在前端是 camelCase——那部分在对应
端点的 schema 里用别名生成器处理，不在这里混用两套。
"""
from __future__ import annotations

from pydantic import BaseModel

from app.models import User


class AdminProfile(BaseModel):
    id: int
    username: str
    email: str
    role: str
    must_change_password: bool


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminProfile


def profile_from_user(user: User) -> AdminProfile:
    # 前端把 email 当 string 用；库里可空，出口统一空串，避免前端 .trim() 崩
    return AdminProfile(
        id=user.id,
        username=user.username,
        email=user.email or "",
        role=user.role,
        must_change_password=user.must_change_password,
    )
