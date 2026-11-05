"""统一错误信封与错误码。

依据 05 §6.1 / §6.2：响应体固定 `{"detail": {"code", "message", "request_id"}}`，
前端按 `code` 分支，不按 message 匹配。错误码只加不改。
"""
from __future__ import annotations

from enum import StrEnum

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    QUESTION_FORBIDDEN = "QUESTION_FORBIDDEN"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    UPLOAD_UNSUPPORTED_TYPE = "UPLOAD_UNSUPPORTED_TYPE"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_INVALID_OUTPUT = "AI_INVALID_OUTPUT"
    AI_INVALID_IMAGE = "AI_INVALID_IMAGE"
    NOT_FOUND = "NOT_FOUND"  # 本 PR 新增：路由未命中，与 QUESTION_NOT_FOUND 区分
    INTERNAL_ERROR = "INTERNAL_ERROR"


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
        # 框架错误（404/405）也走同一信封，避免前端拿到两种形状。
        # NOT_FOUND 是按 05 §6.2「错误码只加不改」新增的一条，不复用 QUESTION_NOT_FOUND——
        # 路径没命中和「错题不存在」是两件事，混用会让前端误判。
        code = (
            ErrorCode.NOT_FOUND
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else ErrorCode.VALIDATION_ERROR
        )
        return JSONResponse(
            _body(request, code, str(exc.detail)),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 不暴露堆栈（05 §9.4）；细节进日志，不进响应
        return JSONResponse(
            _body(request, ErrorCode.INTERNAL_ERROR, "服务内部错误"),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
