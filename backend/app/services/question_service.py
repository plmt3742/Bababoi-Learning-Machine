"""错题业务（05 §6.4）：创建/列表/详情/更新/软删 + 标签同步 + 归属校验。

路由层只做参数校验和鉴权，这里的规则才是契约本体：
- 归属：先查存在性（404），再查归属（403）——两码分开是 05 §6.2 定的
- 创建：question + analysis 任务同一事务落库（12号 §3.2）
- 列表：永远过滤软删除；全文不出门，只出 excerpt（05 §5.3）
"""
from __future__ import annotations

import re

from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.ai.validator import AnalysisResult
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models import (
    GeneratedQuestion,
    GenerationTask,
    Question,
    QuestionTag,
    Tag,
)
from app.schemas.question import (
    QuestionCreate,
    QuestionListItem,
    QuestionUpdate,
    validate_type_payload,
)

# 用户手动打的标签与 AI 分析产出的知识点共用 tags 表，type 用模型默认值
DEFAULT_TAG_TYPE = "knowledge_point"

# LIKE 通配符要转义，否则搜 "100%" 会变成搜 "100任意字符"
_LIKE_SPECIAL = re.compile(r"([%_\\])")


def _get_or_create_tag(session: Session, name: str) -> Tag:
    tag = session.scalar(select(Tag).where(Tag.name == name, Tag.type == DEFAULT_TAG_TYPE))
    if tag is None:
        tag = Tag(name=name, type=DEFAULT_TAG_TYPE)
        session.add(tag)
        session.flush()  # 要 id 才能挂关联
    return tag


def sync_tags(session: Session, question: Question, names: list[str], *, merge: bool = False) -> None:
    """同步标签。

    `merge=False`（默认）是整体替换，用于用户自己编辑标签的场景。
    `merge=True` 给 AI 分析用：AI 知识点是**追加**，不能把用户手动打的标签
    （例如「我的易错」）冲掉——那是真实数据丢失，不是显示问题。
    """
    incoming = [_get_or_create_tag(session, n) for n in dict.fromkeys(names)]
    if merge:
        existing = list(question.tags)
        known = {tag.id for tag in existing}
        question.tags = existing + [tag for tag in incoming if tag.id not in known]
    else:
        question.tags = incoming


def to_storage(value: list | None) -> list | None:
    """pydantic 模型列表 -> 可进 JSON 列的 dict 列表。"""
    return [item.model_dump() for item in value] if value else None


def create(
    session: Session, user_id: int, data: QuestionCreate
) -> tuple[Question, GenerationTask]:
    question = Question(
        user_id=user_id,
        subject=data.subject,
        chapter=data.chapter,
        source_type=data.source_type,
        content_md=data.content_md,
        answer_md=data.answer_md,
        explanation_md=data.explanation_md,
        question_type=data.question_type,
        options=to_storage(data.options),
        blanks=to_storage(data.blanks),
        # 05 §6.4 的 `image_path?` 与 §5.2 的「多题共用同一 image_path」靠这一行落地。
        # 之前 schema 收了、这里没列，于是图片错题建得出来但原图关联丢了——
        # 事后回补只能扫 uploads 目录猜，而文件名是内容寻址的、认不出是谁的哪一页。
        image_path=data.image_path,
    )
    session.add(question)
    session.flush()
    sync_tags(session, question, data.tags)

    # 05 §6.4：保存后自动入队 analysis。BE-006 才有 worker，任务先排队不消费
    task = GenerationTask(
        question_id=question.id, user_id=user_id, stage="analysis", status="queued"
    )
    session.add(task)
    session.commit()
    session.refresh(question)
    return question, task


def get_owned(session: Session, user_id: int, question_id: int) -> Question:
    """取一条属于该用户的未删除错题；不存在/已删 404，别人的 403。"""
    question = session.get(Question, question_id)
    if question is None or question.deleted_at is not None:
        raise ApiError(ErrorCode.QUESTION_NOT_FOUND, "错题不存在或已删除", 404)
    if question.user_id != user_id:
        raise ApiError(ErrorCode.QUESTION_FORBIDDEN, "无权访问他人错题", 403)
    return question


def list_questions(
    session: Session,
    user_id: int,
    *,
    page: int,
    page_size: int,
    subject: str | None,
    tag: str | None,
    mastery_status: str | None,
    q: str | None,
) -> tuple[list[QuestionListItem], int]:
    stmt = select(Question).where(
        Question.user_id == user_id, Question.deleted_at.is_(None)
    )
    if subject:
        stmt = stmt.where(Question.subject == subject)
    if mastery_status:
        stmt = stmt.where(Question.mastery_status == mastery_status)
    if tag:
        stmt = stmt.join(Question.tags).where(Tag.name == tag)
    if q:
        # 05 §5.3：大小写不敏感搜索用 lower + like；转义用户输入里的 % 和 _
        pattern = "%" + _LIKE_SPECIAL.sub(r"\\\1", q) + "%"
        content_hit = func.lower(Question.content_md).like(pattern, escape="\\")
        # PRD 的搜索范围是「题干 + 知识点标签」，所以标签命中也算；
        # 用关联子查询而不是 join，否则一题命中多个标签会在列表里重复出现
        tag_hit = (
            select(QuestionTag.question_id)
            .join(Tag, Tag.id == QuestionTag.tag_id)
            .where(QuestionTag.question_id == Question.id)
            .where(func.lower(Tag.name).like(pattern, escape="\\"))
            .exists()
        )
        stmt = stmt.where(or_(content_hit, tag_hit))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(
        stmt.options(selectinload(Question.tags))
        .order_by(Question.created_at.desc(), Question.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [QuestionListItem.from_question(row) for row in rows], total


def get_detail(session: Session, user_id: int, question_id: int) -> Question:
    """详情要带 tags，预加载免 N+1。"""
    stmt = (
        select(Question)
        .where(Question.id == question_id)
        .options(selectinload(Question.tags))
    )
    question = session.scalar(stmt)
    if question is None or question.deleted_at is not None:
        raise ApiError(ErrorCode.QUESTION_NOT_FOUND, "错题不存在或已删除", 404)
    if question.user_id != user_id:
        raise ApiError(ErrorCode.QUESTION_FORBIDDEN, "无权访问他人错题", 403)
    return question


def list_tasks(session: Session, question_id: int) -> list[GenerationTask]:
    return list(
        session.scalars(
            select(GenerationTask)
            .where(GenerationTask.question_id == question_id)
            .order_by(GenerationTask.created_at.desc(), GenerationTask.id.desc())
        )
    )


def list_generated(
    session: Session, user_id: int, question_id: int
) -> list[GeneratedQuestion]:
    """某错题名下的相似题，按 ①②③ 格位排（ADR-006）。

    用 coalesce 而不是 NULLS LAST：MySQL 8 不认 NULLS LAST 语法，而迁移前的老行
    target_index 是 NULL，得排在三段之后、彼此仍按 created_at 走。
    """
    return list(
        session.scalars(
            select(GeneratedQuestion)
            .where(
                GeneratedQuestion.parent_question_id == question_id,
                GeneratedQuestion.user_id == user_id,
                GeneratedQuestion.deleted_at.is_(None),
            )
            .order_by(
                func.coalesce(GeneratedQuestion.target_index, 9999),
                GeneratedQuestion.created_at,
                GeneratedQuestion.id,
            )
        )
    )


def update(
    session: Session, user_id: int, question_id: int, data: QuestionUpdate
) -> Question:
    question = get_owned(session, user_id, question_id)
    changed = data.model_dump(exclude_unset=True)

    # analysis 是可编辑写回的（05 §6.4），但形状必须还是 AnalysisResult 那一套——
    # 否则前端详情页按字段读的时候会拿到缺 key/错类型的脏结构
    if changed.get("analysis") is not None:
        try:
            changed["analysis"] = AnalysisResult.model_validate(changed["analysis"]).model_dump()
        except ValidationError as exc:
            raise ApiError(
                ErrorCode.VALIDATION_ERROR, f"analysis: {exc.errors()[0]['msg']}", 400
            ) from None

    for field in (
        "subject",
        "chapter",
        "content_md",
        "answer_md",
        "explanation_md",
        "mastery_status",
        "analysis",
    ):
        if field in changed:
            setattr(question, field, changed[field])
    if "tags" in changed:
        sync_tags(session, question, changed["tags"])

    # 题干是空位数/选项校验的输入，改完必须整题复核一遍题型规则
    if "content_md" in changed:
        try:
            validate_type_payload(
                question.question_type, question.content_md, question.options, question.blanks
            )
        except ValidationError as exc:
            session.rollback()
            raise ApiError(
                ErrorCode.VALIDATION_ERROR, exc.errors()[0]["msg"], 400
            ) from None

    session.commit()
    session.refresh(question)
    return question


def soft_delete(session: Session, user_id: int, question_id: int) -> None:
    question = get_owned(session, user_id, question_id)
    question.deleted_at = utcnow()
    session.commit()
