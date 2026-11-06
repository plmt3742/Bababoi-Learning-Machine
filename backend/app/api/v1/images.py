"""图片录入路由（05 §6.8 / BE-014）：上传、鉴权取图、多题文本提取。

三个端点放一个文件是因为它们属于同一件事（图 → 条目），路径仍按 05 各归各位：
`/uploads/images`、`/uploads/{user_id}/{filename}`、`/questions/from-image`。
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import sessionmaker

from app.ai.errors import AIError
from app.api.v1.deps import get_current_user, get_session_factory
from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.models import User
from app.schemas.image import FromImageRequest, ImageExtractionOut, ImageUploadOut
from app.services import extraction_service, image_service

router = APIRouter(tags=["images"])

# 识图是同步等待，所以 AI 层的异常要在这里落成 05 §6.2 的状态码；
# 队列任务那边走的是 task.error_code，没有 HTTP 语义，两边不共用一张表。
_AI_STATUS = {
    "AI_TIMEOUT": 504,
    "AI_PROVIDER_ERROR": 502,
    "AI_INVALID_IMAGE": 422,
    "AI_INVALID_OUTPUT": 422,
}

# 文件名是内容寻址的（同字节必同名），所以长期缓存不会读到旧图；
# 但这张图属于某个用户，private 是必须的。
_CACHE_HEADERS = {"Cache-Control": "private, max-age=31536000, immutable"}


async def _read_capped(file: UploadFile, limit: int) -> bytes:
    """分块读到上限就停，不让一个 2GB 的请求把整张图读进内存再报错。

    先 `await file.read(limit)` 看着更短，但那会把上限以内的字节一次性留在内存里，
    配合 10MB 的上限其实够用——这里保留分块是因为上限本身是可配的（配置调大时行为要对）。
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            raise ApiError(
                ErrorCode.UPLOAD_TOO_LARGE,
                f"图片超过 {settings.image_max_upload_bytes // (1024 * 1024)}MB 上限",
                413,
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/uploads/images", status_code=201)
async def upload_image(
    # Annotated 写法是给 ruff B008 让路的：`file: UploadFile = File(...)` 会被判成
    # 「默认值里调函数」，而这是 FastAPI 官方推荐的声明方式
    file: Annotated[UploadFile, File()],
    user: User = Depends(get_current_user),
) -> ImageUploadOut:
    """存一份"转正 + 剥元数据 + ≤2000px"的 JPEG；原图不留（05 §6.8）。"""
    raw = await _read_capped(file, settings.image_max_upload_bytes)
    stored = image_service.store_upload(user.id, raw)
    return ImageUploadOut(
        image_path=stored.image_path,
        url=stored.url,
        width=stored.width,
        height=stored.height,
    )


@router.get("/uploads/{user_id}/{filename}")
def get_uploaded_image(user_id: int, filename: str, user: User = Depends(get_current_user)) -> Response:
    """鉴权取图。

    落点只按**当前用户**的目录算，路径里的 user_id 对不上就直接 404：
    不给 403，403 等于承认"这文件存在但不属于你"，那是泄露存在性（前端意见单 §一）。
    """
    if user_id != user.id:
        raise ApiError(ErrorCode.NOT_FOUND, "图片不存在", 404)
    data, media_type = image_service.read_for_download(user.id, filename)
    return Response(content=data, media_type=media_type, headers=_CACHE_HEADERS)


@router.post("/questions/from-image")
def extract_from_image(
    body: FromImageRequest,
    user: User = Depends(get_current_user),
    session_factory: sessionmaker = Depends(get_session_factory),
) -> ImageExtractionOut:
    """图片 → 1..N 条可编辑题目条目。不建错题、不分析、不返回 bbox（ADR-004）。"""
    try:
        result = extraction_service.extract_from_image(
            session_factory, user.id, body.image_path, body.subject
        )
    except AIError as exc:
        raise ApiError(ErrorCode(exc.error_code), exc.message,
                       _AI_STATUS.get(exc.error_code, 502)) from None
    return ImageExtractionOut.model_validate(result)
