"""应用装配：只做组装，不放业务。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, health, questions, tasks
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.observability import register_observability, setup_logging
from app.db.session import SessionLocal
from app.services import task_worker

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 密钥类配置在启动时一次查完；留到第一个登录请求只会变成一个没信息的 500
    settings.validate_for_startup()
    # 进程重启把 running 放回队列（12号 §3.3），再拉起后台 worker
    if settings.task_workers_enabled:
        stale = task_worker.reset_stale_running(SessionLocal)
        if stale:
            task_worker.logger.warning("重置了 %d 个卡在 running 的任务", stale)
        stop_event, threads = task_worker.start_workers(
            SessionLocal, settings.task_max_concurrency
        )
    yield
    if settings.task_workers_enabled:
        task_worker.stop_workers(stop_event, threads)


app = FastAPI(title=settings.project_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

register_observability(app)
register_exception_handlers(app)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(questions.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)

# 手工测试台（无鉴权，仅本地/开发用）：backend/static/test-console.html
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
