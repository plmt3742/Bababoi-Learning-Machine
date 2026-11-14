"""草稿路由（05 §6.5b）：GET/PUT/DELETE /drafts/me，业务在 draft_service。"""
from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.drafts import DraftOut, DraftSaveRequest
from app.services import draft_service

router = APIRouter(prefix="/drafts", tags=["drafts"])


def _out(draft) -> DraftOut:
    # 列里是 naive UTC；不补时区的话前端 new Date() 会按本地时区解析，
    # 和 localStorage 里的 ISO 串比较"哪边更新"就全错了
    return DraftOut(
        content=draft.content_json,
        version=draft.version,
        updated_at=draft.updated_at.replace(tzinfo=UTC),
    )


@router.get("/me", response_model=DraftOut, responses={204: {"description": "当前账号没有草稿"}})
def get_draft(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DraftOut | Response:
    draft = draft_service.get(session, user.id)
    if draft is None:
        return Response(status_code=204)
    return _out(draft)


@router.put("/me", response_model=DraftOut)
def save_draft(
    data: DraftSaveRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DraftOut:
    return _out(draft_service.save(session, user.id, data))


@router.delete("/me", status_code=204)
def delete_draft(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    draft_service.delete(session, user.id)
    return Response(status_code=204)
