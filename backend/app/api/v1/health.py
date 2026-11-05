"""健康检查：部署探活与 CI 冒烟用（05 §9.5）。

`/health` 真的连一次库（SELECT 1），不再只看 `database_url` 字符串非空——
BE-002 之后库已经在了，探活却报 not_configured 会让部署清单形同虚设（13号 §4.2）。
`/ready` 额外检查 LLM 配置是否齐备（不调模型）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db import session as db_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _database_state() -> str:
    """取一次连接跑 SELECT 1；失败就返回 unavailable，不把异常抛给探活方。"""
    try:
        with db_session.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001  # 探活的目的就是把坏状态说出来
        logger.warning("数据库探活失败：%s", exc)
        return "unavailable"


def _body(db: str) -> dict:
    return {"status": "ok" if db == "ok" else "degraded", "version": settings.version, "db": db}


@router.get("/health")
def health():
    db = _database_state()
    if db != "ok":
        # 库连不上就 503：compose/nginx 的 healthcheck 靠状态码，不看 body 字段
        return JSONResponse(_body(db), status_code=503)
    return _body(db)


@router.get("/ready")
def ready():
    """就绪检查：DB 连通 + LLM 配置齐备（mock 模式不需要 Key）。不调模型。"""
    db = _database_state()
    llm = "mock" if settings.llm_mock else ("configured" if settings.llm_api_key else "missing_key")
    checks = {"db": db, "llm": llm}
    ok = db == "ok" and llm != "missing_key"
    payload = {"status": "ok" if ok else "degraded", "version": settings.version, "checks": checks}
    return payload if ok else JSONResponse(payload, status_code=503)
