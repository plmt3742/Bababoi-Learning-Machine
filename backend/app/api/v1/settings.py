"""个人设置路由（05 §6.9）。本期只有 BE-026 的生成偏好；BYOK 的 `/settings/ai` 在 BE-020。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.settings import PreferencesOut, PreferencesUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _as_out(owner: User) -> PreferencesOut:
    # 列本身是 NOT NULL DEFAULT 1，读到 None 只可能是历史脏数据或迁移没跑完。
    # 这时按默认开启处理，不返回 null 让前端自己猜（issue #44 验收项"偏好缺失回退 TRUE"）。
    return PreferencesOut(
        enforce_same_question_type=True if owner.enforce_same_question_type is None
        else bool(owner.enforce_same_question_type),
        updated_at=owner.updated_at,
    )


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PreferencesOut:
    """只读当前用户自己的偏好；未登录由 get_current_user 统一 401。"""
    return _as_out(session.get(User, user.id))


@router.put("/preferences", response_model=PreferencesOut)
def put_preferences(
    data: PreferencesUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PreferencesOut:
    """整份覆盖（本期只有一项）。

    用 PUT 不用 PATCH 是有意的：偏好是"当前用户的一份设置"，不是可增量合并的资源，
    以后加第二项时前端必须把两项一起提交，避免出现"只改一项、另一项被默认值悄悄重置"。
    """
    owner = session.get(User, user.id)
    owner.enforce_same_question_type = data.enforce_same_question_type
    session.add(owner)
    session.commit()
    session.refresh(owner)
    return _as_out(owner)
