"""BE-024 识图缓存（05 §6.8）：命中 / 键组成 / 空结果 / 脏数据 / 并发 / 404 语义。"""
from __future__ import annotations

import io
import json

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.ai import prompts
from app.ai.client import LLMResponse, MockLLMClient
from app.models import AiCallLog, VisionExtractCache
from app.services import extraction_service
from tests.conftest import auth_headers, register_user


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (240, 240, 240)).save(buffer, "PNG")
    return buffer.getvalue()


def _upload(client, token: str) -> str:
    resp = client.post(
        "/api/v1/uploads/images",
        files={"file": ("crop.jpg", _image_bytes(), "image/jpeg")},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["image_path"]


def _extract(client, token: str, image_path: str, subject: str | None = None):
    body = {"image_path": image_path}
    if subject is not None:
        body["subject"] = subject
    return client.post(
        "/api/v1/questions/from-image", json=body, headers=auth_headers(token)
    )


class CountingClient(MockLLMClient):
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, operation, messages, **kwargs):
        self.calls += 1
        return super().complete(operation, messages, **kwargs)


class EmptyPageClient(MockLLMClient):
    """第 1 跳就返回"图里没题"，用来验空结果不缓存。"""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, operation, messages, **kwargs):
        self.calls += 1
        system = messages[0]["content"] if messages else ""
        if "步骤：逐题转录" in system:
            return LLMResponse(
                text=json.dumps(
                    {"chapter": None, "questions": [], "warnings": ["没有从图片里辨认出题目"]},
                    ensure_ascii=False,
                ),
                model="mock",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
                finish_reason="stop",
            )
        return super().complete(operation, messages, **kwargs)


@pytest.fixture()
def user(client):
    data = register_user(client)
    return data["access_token"], data["user"]["id"]


def test_second_call_hits_cache_without_model_or_logs(client, db, user, monkeypatch) -> None:
    token, user_id = user
    fake = CountingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    image_path = _upload(client, token)

    first = _extract(client, token, image_path)
    assert first.status_code == 200
    assert fake.calls == 2, "一次识图 = 两跳"

    second = _extract(client, token, image_path)
    assert second.status_code == 200
    assert fake.calls == 2, "第二次应命中缓存，不再调用模型"
    assert second.json() == first.json(), "命中返回与首次完全一致"

    with db() as s:
        row = s.scalar(select(VisionExtractCache).where(VisionExtractCache.user_id == user_id))
        assert row is not None and row.hit_count == 1 and row.last_hit_at is not None
        assert row.question_count == len(first.json()["questions"])
        logs = s.scalar(
            select(func.count(AiCallLog.id)).where(AiCallLog.operation == "vision")
        )
        assert logs == 2, "命中不写 ai_call_logs（成本统计不能虚增）"


def test_subject_is_part_of_key(client, db, user, monkeypatch) -> None:
    token, _ = user
    fake = CountingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    image_path = _upload(client, token)

    assert _extract(client, token, image_path).status_code == 200
    assert fake.calls == 2
    # 学科会进第 2 跳提示词并覆盖条目 subject —— 必须换键
    assert _extract(client, token, image_path, "高等数学").status_code == 200
    assert fake.calls == 4
    with db() as s:
        assert s.scalar(select(func.count(VisionExtractCache.id))) == 2


def test_prompt_version_change_misses(client, db, user, monkeypatch) -> None:
    token, _ = user
    fake = CountingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    image_path = _upload(client, token)

    assert _extract(client, token, image_path).status_code == 200
    monkeypatch.setattr(prompts, "PROMPT_VERSION_VISION_STRUCTURE", "vision_structure_v2")
    assert _extract(client, token, image_path).status_code == 200
    assert fake.calls == 4, "版本变了自然不命中，不用手动清表"


def test_empty_result_is_not_cached(client, db, user, monkeypatch) -> None:
    token, _ = user
    fake = EmptyPageClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    image_path = _upload(client, token)

    assert _extract(client, token, image_path).status_code == 200
    assert _extract(client, token, image_path).status_code == 200
    assert fake.calls == 2, "空结果不缓存：两次都要跑（每次只有第 1 跳）"
    with db() as s:
        assert s.scalar(select(func.count(VisionExtractCache.id))) == 0


def test_corrupt_payload_is_treated_as_miss_and_replaced(client, db, user, monkeypatch) -> None:
    token, _ = user
    fake = CountingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    image_path = _upload(client, token)
    assert _extract(client, token, image_path).status_code == 200

    with db() as s:
        row = s.scalar(select(VisionExtractCache))
        row.payload = {"questions": "坏结构"}
        s.commit()

    resp = _extract(client, token, image_path)
    assert resp.status_code == 200
    assert fake.calls == 4, "脏 payload 当未命中重跑"
    with db() as s:
        rows = list(s.scalars(select(VisionExtractCache)))
        assert len(rows) == 1 and isinstance(rows[0].payload.get("questions"), list)


def test_concurrent_store_keeps_single_row(client, db, user, monkeypatch) -> None:
    token, user_id = user
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: CountingClient())
    image_path = _upload(client, token)
    key = (user_id, image_path.rsplit("/", 1)[-1].split(".", 1)[0], "", "v1", "v2")
    result = {"image_path": image_path, "questions": [{"index": 1}], "warnings": []}

    factory = db
    extraction_service._cache_store(factory, key, result)
    extraction_service._cache_store(factory, key, result)  # 唯一键冲突应被吞掉
    with db() as s:
        assert s.scalar(select(func.count(VisionExtractCache.id))) == 1


def test_missing_file_still_404_before_cache(client, db, user, monkeypatch) -> None:
    token, user_id = user
    fake = CountingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)

    with db() as s:
        s.add(
            VisionExtractCache(
                user_id=user_id,
                image_sha="0" * 16,
                subject_key="",
                hop1_version="vision_text_v1",
                hop2_version="vision_structure_v1",
                payload={"image_path": "x", "questions": [], "warnings": []},
            )
        )
        s.commit()

    resp = _extract(client, token, f"uploads/{user_id}/{'0' * 16}.jpg")
    assert resp.status_code == 404, "缓存不能变成绕过 404 的旁路"
    assert fake.calls == 0


def test_cache_is_per_user(client, db, user, monkeypatch) -> None:
    token_a, _ = user
    fake = CountingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    image_path_a = _upload(client, token_a)
    assert _extract(client, token_a, image_path_a).status_code == 200

    token_b = register_user(client, username="隔壁同学")["access_token"]
    image_path_b = _upload(client, token_b)  # 同一份字节，不同用户目录
    assert _extract(client, token_b, image_path_b).status_code == 200
    assert fake.calls == 4, "不同用户不共享缓存"
