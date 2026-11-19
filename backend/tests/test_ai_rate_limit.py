"""AI 提交限流（BE-016 / 05 §6.2 的 429 `AI_RATE_LIMITED`）。

覆盖三件事：两个桶各自的上限、按用户隔离、窗口过期后恢复。
阈值在这里被 monkeypatch 到很小，测的是判据本身，不是默认值。
"""
from __future__ import annotations

import io
import time

from PIL import Image

from app.core import ai_ratelimit
from tests.conftest import auth_headers, register_user

QUESTION = {
    "subject": "高等数学",
    "content_md": "求 $f(x)=x^2$ 的导数。",
    "question_type": "solve",
}


def _upload(client, token: str) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), (230, 230, 230)).save(buffer, "PNG")
    resp = client.post(
        "/api/v1/uploads/images",
        files={"file": ("crop.png", buffer.getvalue(), "image/png")},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["image_path"]


def _extract(client, token: str, image_path: str):
    return client.post(
        "/api/v1/questions/from-image",
        json={"image_path": image_path},
        headers=auth_headers(token),
    )


def _create(client, token: str):
    return client.post("/api/v1/questions", json=QUESTION, headers=auth_headers(token))


def _generate(client, token: str, question_id: int):
    return client.post(
        f"/api/v1/questions/{question_id}/generate", json={}, headers=auth_headers(token)
    )


def test_vision_limit_is_per_user_and_returns_ai_rate_limited(
    client, db, monkeypatch
) -> None:
    monkeypatch.setattr(ai_ratelimit.vision_limiter, "limit", 1)

    token = register_user(client)["access_token"]
    other = register_user(client, username="小红_02")["access_token"]
    image_path = _upload(client, token)

    assert _extract(client, token, image_path).status_code == 200
    limited = _extract(client, token, image_path)
    assert limited.status_code == 429, limited.text
    assert limited.json()["detail"]["code"] == "AI_RATE_LIMITED"

    # 换一个用户不该被前一个人的额度影响
    assert _extract(client, other, _upload(client, other)).status_code == 200
    # 识图额度不该吃掉入队额度（两个桶分开计）
    assert _create(client, token).status_code == 200


def test_enqueue_bucket_is_shared_by_create_analyze_and_generate(
    client, db, monkeypatch
) -> None:
    monkeypatch.setattr(ai_ratelimit.enqueue_limiter, "limit", 2)

    token = register_user(client)["access_token"]
    created = _create(client, token)
    assert created.status_code == 200, created.text
    question_id = created.json()["question"]["id"]

    # 第 2 次：生题入队，用掉最后一个名额
    assert _generate(client, token, question_id).status_code == 200

    # 第 3 次：重新分析，同一个桶里已经满了
    analyze = client.post(
        f"/api/v1/questions/{question_id}/analyze", headers=auth_headers(token)
    )
    assert analyze.status_code == 429, analyze.text
    assert analyze.json()["detail"]["code"] == "AI_RATE_LIMITED"

    # 另一个用户不受影响
    other = register_user(client, username="小红_02")["access_token"]
    assert _create(client, other).status_code == 200


def test_window_expiry_lets_requests_through_again(client, db, monkeypatch) -> None:
    monkeypatch.setattr(ai_ratelimit.enqueue_limiter, "limit", 1)
    monkeypatch.setattr(ai_ratelimit.enqueue_limiter, "window_s", 0.05)

    token = register_user(client)["access_token"]
    assert _create(client, token).status_code == 200
    assert _create(client, token).status_code == 429

    time.sleep(0.12)
    assert _create(client, token).status_code == 200


def test_vision_bucket_does_not_charge_enqueue_requests(client, db, monkeypatch) -> None:
    monkeypatch.setattr(ai_ratelimit.enqueue_limiter, "limit", 1)

    token = register_user(client)["access_token"]
    image_path = _upload(client, token)
    # 先识图（走 vision 桶），入队额度仍是满的
    assert _extract(client, token, image_path).status_code == 200
    assert _create(client, token).status_code == 200
    assert _create(client, token).status_code == 429
