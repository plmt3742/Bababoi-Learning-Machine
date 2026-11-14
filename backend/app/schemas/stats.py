"""统计概览的响应结构（05 §6.6 / 21号 §2.1）。

字段名与前端 `StatsOverview`（`api/types.ts`）逐字对齐；只此一个形状，
不再提供 `/stats/trends`、`/stats/weak-points` 两个可选端点（21号 §2.1 已取消）。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WeakKnowledgePoint(BaseModel):
    """父题标签聚合出的一条薄弱点；`accuracy` 与总览同口径（0–1）。"""

    name: str
    wrong_count: int
    total_count: int
    accuracy: float


class TrendPoint(BaseModel):
    """某一天（Asia/Shanghai）的练习数；`date` 固定 `YYYY-MM-DD`。"""

    date: str
    practice_count: int
    correct_count: int


class StatsOverview(BaseModel):
    total_questions: int
    total_generated_questions: int
    total_practice_records: int
    accuracy: float
    mastered_count: int
    reviewing_count: int
    unmastered_count: int
    weak_knowledge_points: list[WeakKnowledgePoint]
    recent_trend: list[TrendPoint]
    updated_at: datetime
