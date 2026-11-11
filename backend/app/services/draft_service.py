"""草稿业务（05 §6.5b / docs/product/06 §3）：每账号一份，version 乐观锁。

三条口径：

- **content 原样存取**：后端不解析编辑器内部结构，只管字节上限与版本号；
  字段名虽然叫 `content_json`，存的就是前端给的整个 JSON 对象。
- **乐观锁只认 version**：`client_updated_at` 收下但弃用（浏览器时钟不可信，
  跨设备比时间戳会把新内容当旧的——draft 模型 docstring 同款理由）。
  无草稿时 `base_version` 整个不参与判断，直接建 v1（mock 同款行为）。
- **409 不回传服务端草稿**：错误信封统一 `{"detail": ...}`（21号 §2.2 同款），
  前端要最新内容自己再 GET；06 §3.2 那句「返回服务端最新草稿」没有落地形态，
  以 mock 为准。
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.models import Draft
from app.schemas.drafts import DraftSaveRequest


def get(session: Session, user_id: int) -> Draft | None:
    return session.scalar(select(Draft).where(Draft.user_id == user_id))


def _content_size(content: dict) -> int:
    return len(json.dumps(content, ensure_ascii=False).encode("utf-8"))


def save(session: Session, user_id: int, data: DraftSaveRequest) -> Draft:
    size = _content_size(data.content)
    if size > settings.draft_max_bytes:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"草稿超过 {settings.draft_max_bytes // 1024} KB 上限（当前 {size // 1024} KB），"
            "请删减内容后再保存",
            400,
        )

    draft = get(session, user_id)
    if draft is None:
        draft = Draft(user_id=user_id, content_json=data.content, version=1)
        session.add(draft)
    else:
        if draft.version != data.base_version:
            raise ApiError(
                ErrorCode.DRAFT_VERSION_CONFLICT, "草稿已在其他位置更新，请刷新后重试", 409
            )
        draft.content_json = data.content
        draft.version += 1
    session.commit()
    session.refresh(draft)
    return draft


def delete(session: Session, user_id: int) -> None:
    draft = get(session, user_id)
    if draft is not None:
        session.delete(draft)
        session.commit()
