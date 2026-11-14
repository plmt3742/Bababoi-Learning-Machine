"""图片录入的出入参（05 §6.8 / BE-014）。

提取结果这几个模型**故意和 `schemas/question.py` 里的严格模型不是同一套**：
入库那条路要求"选择题 ≥2 项、label 连续、空位数=答案数、答案非空"，
而识图阶段一张 4 题的页面上有一题没认全，用户仍该看到另外 3 题 + 一条标了
`incomplete` 的可编辑条目。要是这里复用严格模型，识图就会因为一题的瑕疵整单失败。
用户确认之后走 `POST /questions`，那时才用严格模型。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["choice", "blank", "solve"]


class ImageUploadOut(BaseModel):
    image_path: str
    url: str
    width: int
    height: int


class FromImageRequest(BaseModel):
    image_path: str = Field(min_length=1, max_length=255)
    # 学科只是给模型的背景提示，不构成出参：chapter/difficulty 由 analysis 任务负责，
    # 两处都出就会各说各话（前端意见单 §二）
    subject: str | None = Field(default=None, max_length=64)
    # 跳过缓存重跑并覆盖写回：带 incomplete 的结果进缓存后，不刷新就再也拿不到别的结果
    force_refresh: bool = False


class ExtractedOptionOut(BaseModel):
    label: str = ""
    content_md: str = ""


class ExtractedBlankOut(BaseModel):
    index: int = 1
    answer_md: str = ""


class ExtractedQuestionOut(BaseModel):
    index: int
    content_md: str
    question_type: QuestionType
    # 初判三项，对齐前端 ExtractedImageQuestion：只用于预填/展示，
    # 正式 difficulty 与知识点仍由 analysis 写；坏值在服务层已降级成 None
    subject: str | None = None
    chapter: str | None = None
    difficulty: str | None = None
    # 可空是承重的（ADR-004 §5/§6.1）：识图只保证文字，结构不自洽的条目已整条降成文本，
    # 这里不会流出"2 个空位配 1 个答案"那种半套结构。前端按 question_type 渲染即可。
    options: list[ExtractedOptionOut] | None = None
    blanks: list[ExtractedBlankOut] | None = None
    has_figure: bool = False
    warnings: list[str] = Field(default_factory=list)
    incomplete: bool = False


class ImageExtractionOut(BaseModel):
    image_path: str
    questions: list[ExtractedQuestionOut]
    warnings: list[str] = Field(default_factory=list)
    # 前端据此区分"秒回"和"真快"：命中缓存时 cached=true，extracted_at 是首次识别时间
    cached: bool = False
    extracted_at: datetime | None = None
