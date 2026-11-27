"""管理端路由聚合（ADM-002 起）。前缀 `/admin`。

父级分两个 router：登录必须匿名可访问，其余全部默认挂 `require_admin`。
以后新增 `admin/write.py` 只要 include 进 protected，就不会因为忘写依赖而裸奔。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.admin import auth, read
from app.api.v1.deps import require_admin

router = APIRouter()

_public = APIRouter(prefix="/admin", tags=["admin"])
_protected = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

_public.include_router(auth.router)
_protected.include_router(auth.protected_router)
_protected.include_router(read.router)

router.include_router(_public)
router.include_router(_protected)
