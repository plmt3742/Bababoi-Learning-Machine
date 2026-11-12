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

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models import Draft
from app.schemas.drafts import DraftSaveRequest

_CONFLICT_MESSAGE = "草稿已在其他位置更新，请刷新后重试"


def get(session: Session, user_id: int) -> Draft | None:
    return session.scalar(select(Draft).where(Draft.user_id == user_id))


def _content_size(content: dict) -> int:
    return len(json.dumps(content, ensure_ascii=False).encode("utf-8"))


def _conflict() -> ApiError:
    return ApiError(ErrorCode.DRAFT_VERSION_CONFLICT, _CONFLICT_MESSAGE, 409)


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
        try:
            session.commit()
        except IntegrityError:
            # 并发首次保存：唯一约束挡住输家。回读后按版本冲突返回，不能让它变成 500
            session.rollback()
            raise _conflict() from None
        session.refresh(draft)
        return draft

    # 乐观锁必须是原子的：读-比较-写之间另一个请求也可能通过。
    # 条件 UPDATE 由数据库判 rowcount，输的一方（含 base_version=null）拿到 0 → 409。
    result = session.execute(
        update(Draft)
        .where(Draft.user_id == user_id, Draft.version == data.base_version)
        .values(content_json=data.content, version=Draft.version + 1, updated_at=utcnow())
    )
    if result.rowcount != 1:
        session.rollback()
        raise _conflict()
    session.commit()
    session.refresh(draft)
    return draft


def delete(session: Session, user_id: int) -> None:
    draft = get(session, user_id)
    if draft is not None:
        session.delete(draft)
        session.commit()
