"""统计概览（05 §6.6 / 21号 §2.1）：只读当前用户的活数据，不落任何表。

三条口径容易被"看起来对"的实现搞错，集中写在这里：

- **生成题按"父题还活着"过滤**：`question_service.soft_delete` 只软删 questions 行，
  不级联生成题（有意为之：删错题不该连练习流水一起丢）。统计若只滤
  `generated_questions.deleted_at`，用户删掉错题后 `total_generated_questions` 仍 > 0，
  而详情页里一道都点不开。
- **练习流水没有 deleted_at**：`PracticeRecord` 不继承 `SoftDeleteMixin`，所以
  `total_practice_records` 是流水总数（父题删了也还在）。薄弱点聚合要求父题活着，
  否则「已删除错题」的标签会一直挂在薄弱点列表里。
- **趋势按 UTC+8 切天、只取最近 7 天**：中国 1991 年后没有夏令时，固定 +8 与
  `Asia/Shanghai` 等价；用 `ZoneInfo` 反而要额外装 `tzdata`（Windows 本机与 slim
  镜像都没有，会直接抛 `ZoneInfoNotFoundError`），SQLite 也不支持 MySQL 的时区表。
  窗口取 7 天是因为前端把这块标成「近 7 天」。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, lazyload, load_only, selectinload

from app.db.base import utcnow
from app.models import GeneratedQuestion, GenerationTask, PracticeRecord, Question
from app.schemas.stats import StatsOverview, TrendPoint, WeakKnowledgePoint

CHINA_TZ = timezone(timedelta(hours=8))
TREND_DAYS = 7  # 与前端「近 7 天」的说法同窗
WEAK_POINT_LIMIT = 5


def _accuracy(correct: int, total: int) -> float:
    """0–1、三位小数；没有练习时返回 0（契约明确不用 null）。"""
    return round(correct / total, 3) if total else 0.0


def _weak_points(
    questions: list[Question],
    records: list[PracticeRecord],
    parent_by_generated: dict[int, int],
) -> list[WeakKnowledgePoint]:
    tags_by_question = {question.id: [tag.name for tag in question.tags] for question in questions}
    buckets: dict[str, list[int]] = {}  # name -> [wrong, total]
    for record in records:
        parent_id = parent_by_generated.get(record.generated_question_id)
        if parent_id is None or parent_id not in tags_by_question:
            continue
        for name in tags_by_question[parent_id]:
            bucket = buckets.setdefault(name, [0, 0])
            bucket[1] += 1
            if not record.is_correct:
                bucket[0] += 1

    points = [
        WeakKnowledgePoint(
            name=name,
            wrong_count=wrong,
            total_count=total,
            accuracy=_accuracy(total - wrong, total),
        )
        for name, (wrong, total) in buckets.items()
    ]
    # 排序与前端 mock 同序：错得多在前，错得一样看谁正确率更低，再同看练习量，
    # 最后按名字兜底——否则同分条目的顺序在两次请求间会漂。
    points.sort(key=lambda p: (-p.wrong_count, p.accuracy, -p.total_count, p.name))
    return points[:WEAK_POINT_LIMIT]


def _recent_trend(records: list[PracticeRecord]) -> list[TrendPoint]:
    # 前端把这块标成「近 7 天」（首页那句也是），所以窗口必须有界：
    # 只按「有练习的日期」出点，不补齐空白天（21号 §2.1）。
    today = datetime.now(UTC).astimezone(CHINA_TZ).date()
    start = today - timedelta(days=TREND_DAYS - 1)
    buckets: dict[str, list[int]] = {}  # date -> [practice, correct]
    for record in records:
        day = record.created_at.replace(tzinfo=UTC).astimezone(CHINA_TZ).date()
        if not start <= day <= today:
            continue
        bucket = buckets.setdefault(day.isoformat(), [0, 0])
        bucket[0] += 1
        if record.is_correct:
            bucket[1] += 1
    return [
        TrendPoint(date=day, practice_count=practice, correct_count=correct)
        for day, (practice, correct) in sorted(buckets.items())
    ]


def overview(session: Session, user_id: int) -> StatsOverview:
    # load_only 只取统计要用的列（题干全文不拉），noload 掐掉 PracticeRecord 的
    # selectin 关系——模型上那条 lazy="selectin" 会给每条练习再补一次生成题查询
    questions = list(
        session.scalars(
            select(Question)
            .where(Question.user_id == user_id, Question.deleted_at.is_(None))
            .options(
                load_only(Question.id, Question.mastery_status, Question.updated_at),
                selectinload(Question.tags),
            )
        )
    )
    alive_ids = {question.id for question in questions}

    # 一次取全量生成题（含软删）：软删行还要用来把练习流水认回父题
    generated = list(
        session.scalars(
            select(GeneratedQuestion)
            .where(GeneratedQuestion.user_id == user_id)
            .options(
                load_only(
                    GeneratedQuestion.id,
                    GeneratedQuestion.parent_question_id,
                    GeneratedQuestion.deleted_at,
                    GeneratedQuestion.updated_at,
                )
            )
        )
    )
    visible_generated = [
        item
        for item in generated
        if item.deleted_at is None and item.parent_question_id in alive_ids
    ]
    parent_by_generated = {item.id: item.parent_question_id for item in generated}

    records = list(
        session.scalars(
            select(PracticeRecord)
            .where(PracticeRecord.user_id == user_id)
            .options(
                load_only(
                    PracticeRecord.id,
                    PracticeRecord.generated_question_id,
                    PracticeRecord.is_correct,
                    PracticeRecord.created_at,
                ),
                lazyload(PracticeRecord.generated_question),
            )
        )
    )
    correct_records = sum(1 for record in records if record.is_correct)

    mastery = {"mastered": 0, "reviewing": 0, "unmastered": 0}
    for question in questions:
        if question.mastery_status in mastery:
            mastery[question.mastery_status] += 1

    # updated_at = 用户能看见的数据里最新的一次变动；任务只算活父题的
    stamps: list[datetime] = [question.updated_at for question in questions]
    stamps.extend(item.updated_at for item in visible_generated)
    stamps.extend(record.created_at for record in records)
    if alive_ids:
        task_stamps = session.execute(
            select(func.max(GenerationTask.finished_at), func.max(GenerationTask.created_at))
            .where(
                GenerationTask.user_id == user_id,
                GenerationTask.question_id.in_(alive_ids),
            )
        ).one()
        stamps.extend(stamp for stamp in task_stamps if stamp is not None)

    latest = max(stamps) if stamps else utcnow()
    return StatsOverview(
        total_questions=len(questions),
        total_generated_questions=len(visible_generated),
        total_practice_records=len(records),
        accuracy=_accuracy(correct_records, len(records)),
        mastered_count=mastery["mastered"],
        reviewing_count=mastery["reviewing"],
        unmastered_count=mastery["unmastered"],
        weak_knowledge_points=_weak_points(questions, records, parent_by_generated),
        recent_trend=_recent_trend(records),
        updated_at=latest.replace(tzinfo=UTC),
    )
