"""健康检查：部署探活与 CI 冒烟用（05 §9.5）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """db 只报配置状态，不建连接——真正的连通性检查在 BE-002 接上数据库后补。"""
    return {
        "status": "ok",
        "version": settings.version,
        "db": "configured" if settings.database_url else "not_configured",
    }
