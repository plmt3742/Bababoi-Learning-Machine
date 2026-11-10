"""统计路由（05 §6.6）：只有 overview 一个端点，业务在 stats_service。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.stats import StatsOverview
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
def stats_overview(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StatsOverview:
    return stats_service.overview(session, user.id)
