"""管理端路由聚合（ADM-002 起）。前缀 `/admin`，登录端点例外地不挂 require_admin。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import auth, read

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(auth.router)
router.include_router(read.router)
