"""请求标识与访问日志（05 §9.5）。

只记 method / path / status / latency / request_id——不记 body、不记 token 与密码。
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger("bababoi.access")


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def register_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def tag_request_id_and_log(
        request: Request, call_next
    ) -> Response:
        # 复用上游传进来的 id，方便前端把同一次操作串起来
        request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
        request.state.request_id = request_id

        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000)

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s %dms rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
