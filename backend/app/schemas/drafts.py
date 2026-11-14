"""草稿的请求/响应结构（05 §6.5b / docs/product/06 §3.2 / 21号 §2.2）。

`content` 是编辑器完整状态的整体 JSON 对象，后端原样存取、不解析内部字段——
契约只管「字节上限 + 版本乐观锁」，结构合法性归前端编辑器（mock 同款判据：
非对象 400）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DraftSaveRequest(BaseModel):
    """PUT /drafts/me。

    `base_version` 可为 null（前端本地没有服务端版本号时）；
    `client_updated_at` 收下但不参与任何判断——乐观锁只认 version，
    浏览器时钟不可信（draft 模型 docstring 同款理由）。
    """

    content: dict[str, Any]
    base_version: int | None = Field(default=None, ge=0)
    client_updated_at: datetime | None = None


class DraftOut(BaseModel):
    """GET/PUT 的响应体；`updated_at` 由路由层补时区（带 Z 的 UTC）。"""

    content: dict[str, Any]
    version: int
    updated_at: datetime
