"""统一错误信封与错误码。

依据 05 §6.1 / §6.2：响应体固定 `{"detail": {"code", "message", "request_id"}}`，
前端按 `code` 分支，不按 message 匹配。错误码只加不改。
"""
from __future__ import annotations

import logging
from enum import StrEnum

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    QUESTION_FORBIDDEN = "QUESTION_FORBIDDEN"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"  # BE-003 新增：登录失败限流（05 §6.3），与 AI 的 AI_RATE_LIMITED 区分
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    UPLOAD_UNSUPPORTED_TYPE = "UPLOAD_UNSUPPORTED_TYPE"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_INVALID_OUTPUT = "AI_INVALID_OUTPUT"
    AI_INVALID_IMAGE = "AI_INVALID_IMAGE"
    NOT_FOUND = "NOT_FOUND"  # 本 PR 新增：路由未命中，与 QUESTION_NOT_FOUND 区分
    FORBIDDEN = "FORBIDDEN"  # 框架 403（鉴权中间件等），与业务态的 QUESTION_FORBIDDEN 区分
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"  # 框架 405
    TASK_NOT_FOUND = "TASK_NOT_FOUND"  # 05 §6.2 早有成文，BE-006/007 起初误用了 NOT_FOUND
    PRACTICE_DUPLICATE = "PRACTICE_DUPLICATE"  # BE-012：60 秒窗口内相同作答重复提交（05 §6.4）
    INTERNAL_ERROR = "INTERNAL_ERROR"


# 框架 HTTPException 的状态码 → 错误码；没列到的走 VALIDATION_ERROR
_HTTP_STATUS_CODES = {
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
}


class ApiError(Exception):
    """业务层抛这个，别抛裸 HTTPException——否则 code 会丢。"""

    def __init__(self, code: ErrorCode, message: str, http_status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _body(request: Request, code: ErrorCode, message: str) -> dict:
    return {
        "detail": {
            "code": str(code),
            "message": message,
            "request_id": getattr(request.state, "request_id", ""),
        }
    }


def _http_status_to_code(status_code: int) -> ErrorCode:
    """框架 HTTPException 的状态码翻译成错误码。"""
    if status_code in _HTTP_STATUS_CODES:
        return _HTTP_STATUS_CODES[status_code]
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return ErrorCode.INTERNAL_ERROR
    return ErrorCode.VALIDATION_ERROR


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            _body(request, exc.code, exc.message), status_code=exc.http_status
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ()))
        return JSONResponse(
            _body(
                request,
                ErrorCode.VALIDATION_ERROR,
                f"{field}: {first.get('msg', '参数校验失败')}",
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # 框架错误也走同一信封，避免前端拿到两种形状。
        # 按状态码分派而不是统统塞进 VALIDATION_ERROR：405 被当成「参数错」
        # 会让前端去检查表单字段，而真正的问题是方法用错了（13号 §4.8）
        code = _http_status_to_code(exc.status_code)
        return JSONResponse(
            _body(request, code, str(exc.detail)),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 不暴露堆栈（05 §9.4）；但堆栈必须进日志，否则 500 只有一句
        # 「服务内部错误」，request_id 拿不到任何线索（13号 §4.7）
        logger.exception(
            "未预期异常 rid=%s path=%s",
            getattr(request.state, "request_id", ""),
            request.url.path,
        )
        return JSONResponse(
            _body(request, ErrorCode.INTERNAL_ERROR, "服务内部错误"),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
