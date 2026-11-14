"""个人设置路由（05 §6.9）：生成偏好（BE-026）+ 用户自带 AI Key（BE-020 / ADR-007）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.base import utcnow
from app.db.session import get_session
from app.models import User
from app.schemas.settings import (
    AiSettingsOut,
    AiSettingsUpdate,
    PreferencesOut,
    PreferencesUpdate,
)
from app.services import ai_settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


def _as_out(owner: User) -> PreferencesOut:
    # 列本身是 NOT NULL DEFAULT 1，读到 None 只可能是历史脏数据或迁移没跑完。
    # 这时按默认开启处理，不返回 null 让前端自己猜（issue #44 验收项"偏好缺失回退 TRUE"）。
    return PreferencesOut(
        enforce_same_question_type=True if owner.enforce_same_question_type is None
        else bool(owner.enforce_same_question_type),
        updated_at=owner.preference_updated_at or owner.created_at,
    )


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user)) -> PreferencesOut:
    """只读当前用户自己的偏好；未登录由 get_current_user 统一 401。

    `user` 已经是本请求 Session 里的托管对象（get_current_user 与路由共用同一个
    get_session 实例），再 `session.get(User, user.id)` 只是重复查一次同一行。
    """
    return _as_out(user)


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
    user.enforce_same_question_type = data.enforce_same_question_type
    user.preference_updated_at = utcnow()
    session.commit()
    session.refresh(user)
    return _as_out(user)


@router.get("/ai", response_model=AiSettingsOut)
def get_ai_settings(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AiSettingsOut:
    """未配置时返回 `configured=false`，不是 404——前端按这个字段决定显示"未启用/已配置"。"""
    return ai_settings_service.get_settings(session, user.id)


@router.put("/ai", response_model=AiSettingsOut)
def put_ai_settings(
    data: AiSettingsUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AiSettingsOut:
    """整份覆盖；返回只含掩码，原始 Key 不回传。"""
    return ai_settings_service.save_settings(session, user.id, data)


@router.delete("/ai", status_code=204)
def delete_ai_settings(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    """删除后回退系统 Key；没有配置时也返回 204（幂等）。"""
    ai_settings_service.delete_settings(session, user.id)
    return Response(status_code=204)
