"""应用装配：只做组装，不放业务。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, health, questions
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.observability import register_observability, setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 密钥类配置在启动时一次查完；留到第一个登录请求只会变成一个没信息的 500
    settings.validate_for_startup()
    yield


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
