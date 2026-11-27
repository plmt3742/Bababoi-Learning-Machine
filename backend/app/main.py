"""应用装配：只做组装，不放业务。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, drafts, health, images, practice, questions, stats, tasks

# 取 router 别名而不是 import app.api.v1.settings：这个名字下面一行就要给
# app.core.config.settings 用，两个都叫 settings 会互相覆盖，
# 症状是 settings.api_prefix 报错——很难一眼看出来是导入撞名
from app.api.v1.settings import router as settings_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.observability import register_observability, setup_logging
from app.core.rate_limit import validate_rate_limit_config
from app.db.session import SessionLocal
from app.services import task_worker, vision_job_service, vision_worker

logger = logging.getLogger(__name__)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 密钥类配置在启动时一次查完；留到第一个登录请求只会变成一个没信息的 500
    settings.validate_for_startup()
    # 限流额度也是配置：解析失败在启动时就炸，别等第一个登录请求
    validate_rate_limit_config()
    # 进程重启把 running 放回队列（12号 §3.3），再拉起后台 worker
    if settings.task_workers_enabled:
        stale = task_worker.reset_stale_running(SessionLocal)
        if stale:
            task_worker.logger.warning("重置了 %d 个卡在 running 的任务", stale)
        stop_event, threads = task_worker.start_workers(
            SessionLocal, settings.task_max_concurrency
        )
        # 识图任务：启动自愈 + 独立线程组（与生题互不饿死）
        recovered = vision_job_service.recover_stale(SessionLocal)
        if recovered:
            logger.warning("重置/终止了 %d 个卡住的识图任务", recovered)
        vision_stop, vision_threads = vision_worker.start_workers(
            SessionLocal, settings.vision_max_concurrency
        )
    yield
    if settings.task_workers_enabled:
        task_worker.stop_workers(stop_event, threads)
        vision_worker.stop_workers(vision_stop, vision_threads)


app = FastAPI(title=settings.project_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    # 跨源直连时浏览器默认读不到 Retry-After（同源/nginx 代理部署不受影响）
    expose_headers=["Retry-After"],
)

register_observability(app)
register_exception_handlers(app)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(questions.router, prefix=settings.api_prefix)
# images 里也有 /questions/from-image，放在 questions 之后，避免抢走 /questions/{id} 的形状
app.include_router(images.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(practice.router, prefix=settings.api_prefix)
app.include_router(drafts.router, prefix=settings.api_prefix)
app.include_router(stats.router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)

# 手工测试台（无鉴权，仅本地/开发用）：backend/static/test-console.html
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
