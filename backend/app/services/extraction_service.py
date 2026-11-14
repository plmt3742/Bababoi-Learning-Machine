"""识图提取（BE-014 / 05 §7.0）：把已上传的图转成 1..N 条可编辑题目条目。

链路上的三个决定，都是实测逼出来的，不是风格问题：

1. **同步跑，超时不自动重试**（14 号 §5-4）。一次识图实测开 `response_format=json_object`
   是 7.7s，不开会跑偏到 44.1s / 7265 token；再叠一层重试等于把用户的等待时间翻倍，
   而识图失败用户本来就能立刻"重传/改文本"。
2. **只有坏输出重试 1 次**（05 §7.0）。解析不出来、整个 JSON 形状不对，重抛一次是划算的；
   这一层由 pipeline 的 `retry_limit=1` 承担。
3. **校验失败对外报 `AI_INVALID_IMAGE`，不是 `AI_INVALID_OUTPUT`**。
4. **命中缓存不写 `ai_call_logs`**（BE-024）：命中不是一次模型调用，写进去会让
   成本/延迟统计虚增；命中次数记在 `vision_extract_cache.hit_count`。对用户来说这两件事
   是同一句"这张图没认出来"，而后者的措辞会把排查方向带偏到 prompt 上。
   缓存命中要能看出来（出参 `cached` / `extracted_at`），也要能退出（请求 `force_refresh`）。
"""
from __future__ import annotations

import logging
import math
import threading
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from pydantic import ValidationError
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.ai import prompts, validator
from app.ai.client import OPERATION_VISION, build_llm_client
from app.ai.errors import AIError, AIInvalidImageError, AIInvalidOutputError, AITruncatedError
from app.ai.pipeline import run as pipeline_run
from app.core.config import settings
from app.core.errors import ApiError, ErrorCode
from app.db.base import utcnow
from app.models import VisionExtractCache
from app.schemas.image import ImageExtractionOut
from app.services import ai_log, image_service

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def _llm_client():
    """识图用的客户端；测试 monkeypatch 这个函数换替身（和 task_worker 同一套路）。

    这里挂的是连接池，每个请求新建一个就等于每张图重新 TLS 握手，所以按进程缓存一份。
    """
    global _client
    with _client_lock:
        if _client is None:
            _client = build_llm_client()
        return _client


class _CacheKey(NamedTuple):
    user_id: int
    image_sha: str
    subject_key: str
    model: str
    hop1_version: str
    hop2_version: str


def _cache_model() -> str:
    """产出这份结果的模型身份。mock 单列一档，否则本地假结果会命中到真模型/演示库。"""
    return "mock" if settings.llm_mock else settings.llm_model


def _cache_key(user_id: int, image_path: str, subject: str | None) -> _CacheKey | None:
    """用户 + 图内容 + 学科 + 模型 + 两跳版本；路径不合法就不缓存。"""
    match = image_service.IMAGE_PATH_RE.match(image_path or "")
    if match is None or int(match.group(1)) != user_id:
        return None
    image_sha = match.group(2).split(".", 1)[0]
    return _CacheKey(
        user_id=user_id,
        image_sha=image_sha,
        subject_key=(subject or "").strip(),
        model=_cache_model(),
        hop1_version=prompts.PROMPT_VERSION_VISION_TEXT,
        hop2_version=prompts.PROMPT_VERSION_VISION_STRUCTURE,
    )


def _cache_where(key: _CacheKey):
    """缓存行的完整键条件；读写删冷四处共用，少一处漏 model 就是一个脏命中。"""
    return (
        VisionExtractCache.user_id == key.user_id,
        VisionExtractCache.image_sha == key.image_sha,
        VisionExtractCache.subject_key == key.subject_key,
        VisionExtractCache.model == key.model,
        VisionExtractCache.hop1_version == key.hop1_version,
        VisionExtractCache.hop2_version == key.hop2_version,
    )


def _cache_load(session_factory: sessionmaker, key: _CacheKey) -> dict | None:
    with session_factory() as session:
        row = session.scalar(select(VisionExtractCache).where(*_cache_where(key)))
        if row is None:
            return None
        try:
            payload = ImageExtractionOut.model_validate(row.payload).model_dump()
        except ValidationError:
            # 旧结构/脏数据：删掉当未命中，别让一次 500 教用户清缓存
            session.delete(row)
            session.commit()
            return None
        row.hit_count += 1
        row.last_hit_at = utcnow()
        session.commit()
        # extracted_at 用首次生成时间（存在 payload 里），这里只补"这次是命中"
        payload["cached"] = True
        return payload


def _acquire_force_slot(session_factory: sessionmaker, key: _CacheKey) -> int:
    """占用一次强刷额度：0 = 占到了，>0 = 冷却剩余秒数。

    在调用模型**之前**占用——超时/截断同样是 17–90s 的开销，失败路径不能绕过冷却。
    `UPDATE ... WHERE last_forced_at` 带条件，两个并发强刷只有一个能占到。
    """
    now = utcnow()
    cutoff = now - timedelta(seconds=settings.vision_force_refresh_cooldown_s)
    with session_factory() as session:
        row_id = session.scalar(select(VisionExtractCache.id).where(*_cache_where(key)))
        if row_id is None:
            # 没有缓存行 = 没有旧结果可反复重烧，等同一次普通识别，不占冷却
            return 0
        taken = session.execute(
            update(VisionExtractCache)
            .where(
                VisionExtractCache.id == row_id,
                or_(
                    VisionExtractCache.last_forced_at.is_(None),
                    VisionExtractCache.last_forced_at <= cutoff,
                ),
            )
            .values(last_forced_at=now)
        )
        session.commit()
        if taken.rowcount:
            return 0
        last = session.scalar(
            select(VisionExtractCache.last_forced_at).where(
                VisionExtractCache.id == row_id
            )
        )
    if last is None:
        return 0
    remaining = settings.vision_force_refresh_cooldown_s - (utcnow() - last).total_seconds()
    return max(1, math.ceil(remaining))


def _cache_delete(session_factory: sessionmaker, key: _CacheKey) -> None:
    with session_factory() as session:
        row = session.scalar(select(VisionExtractCache).where(*_cache_where(key)))
        if row is not None:
            session.delete(row)
            session.commit()


def _payload_for_storage(result: dict) -> dict:
    """JSON 列只认可序列化的值；extracted_at 这种 datetime 要转 ISO 字符串。"""
    return ImageExtractionOut.model_validate(result).model_dump(mode="json")


def _created_at_naive_utc(result: dict) -> datetime:
    value = result.get("extracted_at")
    if isinstance(value, datetime):
        return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value
    return utcnow()


def _cache_store(
    session_factory: sessionmaker, key: _CacheKey, result: dict, *, overwrite: bool = False
) -> None:
    questions = result.get("questions") or []
    if not questions:
        # 空结果不缓存：更可能是传错图，钉死一次误操作没意义。
        # 但强刷出空结果时旧行必须删——否则下一次普通请求会命中早已作废的旧识别
        if overwrite:
            _cache_delete(session_factory, key)
        return
    payload = _payload_for_storage(result)
    created_at = _created_at_naive_utc(result)
    with session_factory() as session:
        if overwrite:
            row = session.scalar(select(VisionExtractCache).where(*_cache_where(key)))
            if row is not None:
                # force_refresh：新结果覆盖旧行，命中统计归零（这一行还没被命中过）
                row.payload = payload
                row.question_count = len(questions)
                row.has_incomplete = any(item.get("incomplete") for item in questions)
                row.created_at = created_at
                row.hit_count = 0
                row.last_hit_at = None
                row.last_forced_at = utcnow()
                session.commit()
                return
        session.add(
            VisionExtractCache(
                user_id=key.user_id,
                image_sha=key.image_sha,
                subject_key=key.subject_key,
                model=key.model,
                hop1_version=key.hop1_version,
                hop2_version=key.hop2_version,
                payload=payload,
                question_count=len(questions),
                has_incomplete=any(item.get("incomplete") for item in questions),
                created_at=created_at,
                last_forced_at=utcnow() if overwrite else None,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            # 并发同图：唯一键只留一行，后写的丢掉即可
            session.rollback()


def extract_from_image(
    session_factory: sessionmaker,
    user_id: int,
    image_path: str,
    *,
    subject: str | None = None,
    force_refresh: bool = False,
) -> dict:
    """返回 `{"image_path", "questions": [ExtractedQuestion], "warnings": [str],
    "cached": bool, "extracted_at": datetime}`。

    两跳（BE-024 / 05 §6.8）：第 1 跳只转录（图 → 文本 + chapter），第 2 跳只结构化
    （文本 → 现有 ExtractedQuestion 形状）。对外仍是同一个端点、同一次 HTTP。
    `force_refresh=True` 跳过缓存读，成功后覆盖写回（给"重新识别"一个出口）；
    连续强刷受冷却限制（429 `VISION_REFRESH_COOLDOWN`，额度在调用模型前占用，失败也计），
    否则一次重跑 17–90s 就是成本放大器。
    """
    # 缓存不能变成绕过 404 的旁路：文件归属先校验（不存在/不属于本人仍旧 404）
    image_service.resolve_user_file(user_id, image_path)
    key = _cache_key(user_id, image_path, subject)
    if key is not None:
        if force_refresh:
            try:
                wait_s = _acquire_force_slot(session_factory, key)
            except Exception as exc:  # noqa: BLE001 冷却检查失败不能把识图打挂，按放行处理
                logger.warning("识图缓存冷却检查失败（user=%s）：%s", user_id, exc)
                wait_s = 0
            if wait_s > 0:
                raise ApiError(
                    ErrorCode.VISION_REFRESH_COOLDOWN,
                    f"刚重新识别过，请 {wait_s} 秒后再试",
                    429,
                )
        else:
            try:
                cached = _cache_load(session_factory, key)
            except Exception as exc:  # noqa: BLE001 缓存读失败不能拖垮识图，按未命中处理
                # 典型场景是本地库没跑迁移（表不存在）：一行警告足够，别每个请求刷一次 traceback
                logger.warning("识图缓存读取失败（user=%s）：%s", user_id, exc)
                cached = None
            if cached is not None:
                logger.info(
                    "识图缓存命中（user=%s sha=%s subject=%r）",
                    user_id,
                    key.image_sha,
                    key.subject_key,
                )
                cached["image_path"] = image_path
                return cached

    extracted_at = datetime.now(UTC)
    data_url = image_service.data_url_for_llm(user_id, image_path)
    client = _llm_client()

    transcript = _hop(
        session_factory,
        user_id,
        client,
        messages=prompts.vision_text_messages(data_url),
        version=prompts.PROMPT_VERSION_VISION_TEXT,
        # 05 §6.8：转录开思考；实测密页（p4）24000 才完整（17251 输出 token），
        # 16000 会在第 1 跳直接截断
        max_tokens=24000,
        thinking="adaptive",
        validate=validator.validate_transcript,
    )
    if not transcript["questions"]:
        # 图里没题是正常结果，不再白花第二跳；只留一条转录日志。
        # 强刷出空结果时旧行必须删：否则下一次普通请求会命中早已作废的旧识别
        if key is not None and force_refresh:
            try:
                _cache_delete(session_factory, key)
            except Exception as exc:  # noqa: BLE001 删缓存失败不能把正常返回变成 500
                logger.warning("识图缓存清理失败（user=%s）：%s", user_id, exc)
        return {
            "image_path": image_path,
            "questions": [],
            "warnings": transcript["warnings"],
            "extracted_at": extracted_at,
        }

    structure = _hop(
        session_factory,
        user_id,
        client,
        messages=prompts.vision_structure_messages(transcript, subject),
        version=prompts.PROMPT_VERSION_VISION_STRUCTURE,
        max_tokens=8000,
        thinking="disabled",
        validate=lambda raw: validator.validate_extraction(
            validator.normalize_blank_markers(raw)
        ),
    )

    chapter = transcript["chapter"]
    chosen = subject.strip() if subject and subject.strip() else None
    items = structure["questions"]
    for item in items:
        # 硬约束 1：chapter 只认第 1 跳（页眉不是题目，第 2 跳看不到）
        item.chapter = chapter
        if chosen:
            # 17 号 §三 规则 1：用户已经选了学科，就别让模型猜的值覆盖它
            item.subject = chosen
    # 第 1 跳的「第 N 题被裁掉」类警告要落到条目上，前端确认步骤才拦得住
    validator.attach_transcript_warnings(
        transcript["warnings"], items, transcript_count=len(transcript["questions"])
    )
    result = {
        "image_path": image_path,
        # 出 model_dump 而不是 validator 的模型对象：响应模型是 schemas.image 那一套，
        # 跨模块的 pydantic 实例不会自动互认，直接把服务返回值变成可序列化的 dict 更干净
        "questions": [item.model_dump() for item in items],
        "warnings": list(transcript["warnings"]) + list(structure["warnings"]),
        "extracted_at": extracted_at,
    }
    if key is not None:
        try:
            _cache_store(session_factory, key, result, overwrite=force_refresh)
        except Exception as exc:  # noqa: BLE001 缓存写失败不能把已经识别成功的请求变成 500
            logger.warning("识图缓存写入失败（user=%s）：%s", user_id, exc)
    return result


def _hop(
    session_factory: sessionmaker,
    user_id: int,
    client,
    *,
    messages: list[dict],
    version: str,
    max_tokens: int,
    thinking: str,
    validate,
):
    """跑一跳：调用、校验、失败写一行日志（prompt_version 按跳分开）。"""
    try:
        result = pipeline_run(
            client,
            OPERATION_VISION,
            messages,
            custom_validate=validate,
            retry_limit=1,
            max_tokens=max_tokens,
            thinking=thinking,
        )
    except AITruncatedError as exc:
        # 实测一张真实教材照片 4 道题就吃掉 6776 输出 token；一页更密的题确实会顶到。
        # 这时候用户能做的只有把图裁小一点，所以文案要给动作。
        message = "这张图题目太多，识别结果被截断了；请裁剪成几次再上传"
        ai_log.write_call_log(
            session_factory, user_id, OPERATION_VISION, status="error",
            error_code="AI_INVALID_IMAGE", raw_text=exc.raw_text,
            prompt_version_override=version,
        )
        raise AIInvalidImageError(message, raw_text=exc.raw_text) from None
    except AIInvalidOutputError as exc:
        ai_log.write_call_log(
            session_factory, user_id, OPERATION_VISION, status="error",
            error_code="AI_INVALID_IMAGE", raw_text=exc.raw_text,
            prompt_version_override=version,
        )
        raise AIInvalidImageError(exc.message, raw_text=exc.raw_text) from None
    except AIError as exc:
        # 超时/供应商错误也要留一条：没有这行，识图失败在成本与延迟统计里就是隐身的
        ai_log.write_call_log(
            session_factory, user_id, OPERATION_VISION, status="error",
            error_code=exc.error_code, raw_text=exc.raw_text,
            prompt_version_override=version,
        )
        raise

    ai_log.write_call_log(
        session_factory, user_id, OPERATION_VISION, status="success",
        usage=result.usage, raw_text=result.usage.text,
        prompt_version_override=version,
    )
    return result.value
