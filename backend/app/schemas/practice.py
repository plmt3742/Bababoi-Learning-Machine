"""练习记录的请求/响应结构（05 §5.2 / §6.4）。

数值范围（duration 0–3600）在这里校验，不落 DB CHECK——SQLite 与 MySQL
用同一套 DDL，CHECK 的表达能力两边不对等（见 models/records.py 同款注释）。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PracticeRecordCreate(BaseModel):
    """POST /practice-records；05 §6.4 的扁平结构。"""

    generated_question_id: int
    user_answer: str | None = Field(default=None, max_length=8000)
    is_correct: bool
    duration_seconds: int = Field(ge=0, le=3600)


class PracticeRecordOut(BaseModel):
    """练习流水；不回传 user_id（永远是当前用户自己的）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    generated_question_id: int
    user_answer: str | None
    is_correct: bool
    duration_seconds: int
    created_at: datetime


class PracticeRecordPage(BaseModel):
    """分页信封（05 §6.1）。"""

    items: list[PracticeRecordOut]
    total: int
    page: int
    page_size: int


# 防重复窗口：同用户、同生成题、同答案、同判定的提交在窗口内视为重复点击
DUPLICATE_WINDOW_SECONDS = 60
