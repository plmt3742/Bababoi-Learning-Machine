"""识图任务化的请求/响应结构（05 §6.8）。"""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.image import ImageExtractionOut


class VisionJobErrorOut(BaseModel):
    code: str
    message: str


class VisionJobOut(BaseModel):
    """轮询响应：status=done 才带 result，failed 才带 error。"""

    job_id: int
    status: str
    result: ImageExtractionOut | None = None
    error: VisionJobErrorOut | None = None


class VisionJobSubmitOut(BaseModel):
    """提交响应：job_id 为 None 表示命中缓存、结果已直接返回。"""

    job_id: int | None = None
    status: str
    reused: bool = False
    queue_position: int | None = None
    estimated_wait_s: int | None = None
    result: ImageExtractionOut | None = None
