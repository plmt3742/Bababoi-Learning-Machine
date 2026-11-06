"""图片录入接口测试（BE-014）：上传、鉴权取图、多题文本提取。

题图都在测试里用 Pillow 现造，仓库不放真实学生题图（05 §6.8 / 14 号 §5-6）。
识图调用走 MockLLMClient（conftest 全量强制 LLM_MOCK=true），不发网络请求。
"""
from __future__ import annotations

import io
import os

import pytest
from PIL import Image
from sqlalchemy import select

from app.ai.errors import AITimeoutError
from app.core.config import settings
from app.models import AiCallLog
from app.services import extraction_service, image_service, task_worker
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def token_and_user(client):
    """注册一个用户，返回 (token, user_id)。

    user_id 从 /auth/me 现取，不靠"第一个注册的就是 1 号"这种隐含顺序——
    测试一旦并行或加用例，那种假设就会静默错位。
    """
    token = register_user(client)["access_token"]
    me = client.get("/api/v1/auth/me", headers=auth_headers(token)).json()
    return token, me["id"]


def image_bytes(width: int = 1600, height: int = 1200, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (240, 240, 240)).save(buffer, fmt)
    return buffer.getvalue()


def jpeg_with_exif() -> tuple[bytes, tuple[int, int]]:
    """一张"手机竖拍"的替身：像素是横的 200x100，EXIF orientation=6 表示要转正成 100x200。"""
    image = Image.new("RGB", (200, 100), (10, 20, 30))
    for x in range(40):
        for y in range(20):
            image.putpixel((x, y), (250, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation
    exif[0x010F] = "MAKER-should-be-gone"  # Make：剥元数据要验的就是它没了
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif.tobytes())
    return buffer.getvalue(), (100, 200)


def upload(client, token: str, data: bytes, filename: str = "crop.jpg", mime: str = "image/jpeg"):
    return client.post(
        "/api/v1/uploads/images",
        files={"file": (filename, data, mime)},
        headers=auth_headers(token),
    )


def stored_image(image_path: str):
    """按库里的标识符把文件开出来（走的是服务层同一个解析）。"""
    match = image_service.IMAGE_PATH_RE.match(image_path)
    path = image_service._dir_for(int(match.group(1))) / match.group(2)
    return Image.open(path), path


def test_upload_returns_path_url_and_the_size_actually_stored(client, db, token_and_user) -> None:
    token, user_id = token_and_user
    resp = upload(client, token, image_bytes(3000, 2000), "page.png", "image/png")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["image_path"].startswith(f"uploads/{user_id}/")
    assert body["url"] == f"/api/v1/{body['image_path']}"
    # 长边 3000 被压到 ≤2000，且返回的就是落盘那份的实际尺寸（前端按它占位防跳版）
    assert max(body["width"], body["height"]) <= settings.image_max_edge_px
    stored, _ = stored_image(body["image_path"])
    assert (stored.width, stored.height) == (body["width"], body["height"])
    assert stored.format == "JPEG"  # 进来的不管是 PNG 还是 WebP，出去只有 JPEG 一种


def test_upload_strips_exif_and_applies_orientation(client, db, token_and_user) -> None:
    token, _ = token_and_user
    raw, expected = jpeg_with_exif()
    body = upload(client, token, raw).json()

    stored, _ = stored_image(body["image_path"])
    assert (stored.width, stored.height) == expected, "orientation=6 该被转正"
    assert body["width"] == expected[0] and body["height"] == expected[1]
    leftover = stored.getexif()
    assert 0x0112 not in leftover and 0x010F not in leftover, f"元数据没剥干净：{dict(leftover)}"


def test_upload_rejects_non_image_and_disallowed_format(client, db, token_and_user) -> None:
    token, _ = token_and_user
    resp = upload(client, token, "这不是图片，只是改了个后缀".encode())
    assert resp.status_code == 415, resp.text
    assert resp.json()["detail"]["code"] == "UPLOAD_UNSUPPORTED_TYPE"

    resp = upload(client, token, image_bytes(200, 200, fmt="GIF"), "x.gif", "image/gif")
    assert resp.status_code == 415
    assert resp.json()["detail"]["code"] == "UPLOAD_UNSUPPORTED_TYPE"


def test_upload_rejects_oversized_before_touching_the_format(
    client, db, token_and_user, monkeypatch
) -> None:
    """体积门槛在格式识别之前：一个 300KB 的坏文件不该先被 Pillow 解一遍再报错。

    这里用随机字节而不是"大图"——真实 1500x1500 的纯色 PNG 才几 KB，
    拿它当"超限"用例会得到一个 201，测的是假设不是行为。
    """
    token, _ = token_and_user
    monkeypatch.setattr(settings, "image_max_upload_bytes", 200 * 1024)
    resp = upload(client, token, os.urandom(300 * 1024))
    assert resp.status_code == 413, resp.text
    assert resp.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"


def test_same_image_uploads_once(client, db, token_and_user) -> None:
    """内容寻址：同一张图传两次只落一份文件——也因此 immutable 缓存才安全。"""
    token, _ = token_and_user
    first = upload(client, token, image_bytes(800, 600)).json()
    second = upload(client, token, image_bytes(800, 600)).json()
    assert first["image_path"] == second["image_path"]
    _, path = stored_image(first["image_path"])
    assert list(path.parent.iterdir()) == [path], "第二张不该又落一个文件"


def test_get_image_requires_auth_and_hides_other_users(client, db, token_and_user) -> None:
    token, user_id = token_and_user
    body = upload(client, token, image_bytes(400, 300)).json()
    filename = body["image_path"].rsplit("/", 1)[1]

    resp = client.get(f"/api/v1/uploads/{user_id}/{filename}")
    assert resp.status_code == 401  # 没带 token

    resp = client.get(f"/api/v1/uploads/{user_id}/{filename}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    cache = resp.headers["cache-control"]
    assert "private" in cache and "immutable" in cache

    other_token = register_user(client, "路人_02")["access_token"]
    resp = client.get(f"/api/v1/uploads/{user_id}/{filename}", headers=auth_headers(other_token))
    # 404 而不是 403：403 等于承认"这文件存在但不属于你"
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "filename",
    ["notahash.jpg", "1234567890abcdefg.jpg", "1234567890abcdef.exe", "%2e%2e%2fsecret.jpg"],
)
def test_get_image_accepts_only_content_addressed_names(client, db, token_and_user, filename) -> None:
    """文件名必须是 16 位十六进制 + 三种后缀；别的形状一律 404（顺带堵死路径穿越）。"""
    token, user_id = token_and_user
    resp = client.get(f"/api/v1/uploads/{user_id}/{filename}", headers=auth_headers(token))
    assert resp.status_code == 404


def test_image_path_parser_refuses_traversal(client, db, token_and_user) -> None:
    """路由之外再验一层解析器本身：任何带 `..` 或非本前缀的标识符都不给解析。"""
    for hostile in (
        "uploads/1/../../2/0000000000000000.jpg",
        "../uploads/1/0000000000000000.jpg",
        "uploads/0000000000000000.jpg",
        "",
    ):
        with pytest.raises(Exception) as excinfo:
            image_service.resolve_user_file(1, hostile)
        assert excinfo.value.http_status == 404  # 一律"不存在"，不说为什么不存在


def _extract(client, token: str, image_path: str, subject: str | None = None):
    payload = {"image_path": image_path}
    if subject:
        payload["subject"] = subject
    return client.post("/api/v1/questions/from-image", json=payload, headers=auth_headers(token))


def test_from_image_returns_editable_items(client, db, token_and_user) -> None:
    """mock 输出把提取的四条分支各来一条，正好验 ①②③④ 的展示语义。"""
    token, _ = token_and_user
    image_path = upload(client, token, image_bytes(900, 700)).json()["image_path"]

    resp = _extract(client, token, image_path, "高等数学")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["image_path"] == image_path
    assert [q["index"] for q in body["questions"]] == [1, 2, 3, 4]

    solve, blank, degraded, figure = body["questions"]
    assert solve["question_type"] == "solve" and solve["incomplete"] is False
    # 空位数 = 答案数：结构自洽，就按填空题原样交给用户
    assert blank["question_type"] == "blank" and len(blank["blanks"]) == 2
    # 2 个空只读出 1 个答案：不半套返回，整条降级成文本 + 说清去哪补结构
    assert degraded["question_type"] == "solve" and degraded["incomplete"] is True
    assert degraded["blanks"] is None and degraded["options"] is None
    assert any("空位" in w and "文本题" in w for w in degraded["warnings"])
    assert figure["has_figure"] is True and any("含图" in w for w in figure["warnings"])
    # 带 warning 就必须带 incomplete：前端确认步骤只看标志位（17 号 §四-4）
    assert figure["incomplete"] is True
    # 提取阶段不返回答案/解析：那是 analysis 的事，两处都出就会抢真源
    assert "answer_md" not in solve and "explanation_md" not in solve
    # 17 号对齐清单 §三 规则 1：请求带了 subject 就一律用请求值，模型猜的（mock 第 2 条写"线性代数"）被覆盖
    assert {q["subject"] for q in body["questions"]} == {"高等数学"}
    # 初判另两项：好值透出、非法档位降级成 None
    assert (solve["chapter"], solve["difficulty"]) == ("习题 7.1", "medium")
    assert blank["chapter"] == "复习题六"
    assert blank["difficulty"] is None, "非法档位必须降级成 None，而不是把整条题目丢掉"
    assert (figure["chapter"], figure["difficulty"]) == (None, None)

    with db() as s:
        logs = s.scalars(select(AiCallLog).where(AiCallLog.operation == "vision")).all()
        assert logs[-1].status == "success"
        assert logs[-1].prompt_version == "vision_extract_v2"


def test_from_image_rejects_other_users_path_and_missing_file(client, db, token_and_user) -> None:
    token, user_id = token_and_user
    image_path = upload(client, token, image_bytes(600, 500)).json()["image_path"]

    other_token = register_user(client, "路人_03")["access_token"]
    assert _extract(client, other_token, image_path).status_code == 404

    fake = f"uploads/{user_id}/0000000000000000.jpg"
    assert _extract(client, token, fake).status_code == 404


def test_from_image_timeout_is_504_and_not_retried(client, db, token_and_user, monkeypatch) -> None:
    """14 号 §5-4：识图超时不自动重试——用户能立刻重传，不该再等一轮 44s。"""
    token, _ = token_and_user
    image_path = upload(client, token, image_bytes(600, 500)).json()["image_path"]

    class TimeoutClient:
        def __init__(self):
            self.calls = 0

        def complete(self, operation, messages):
            self.calls += 1
            raise AITimeoutError("识图超时了")

    fake = TimeoutClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    resp = _extract(client, token, image_path)
    assert resp.status_code == 504, resp.text
    assert resp.json()["detail"]["code"] == "AI_TIMEOUT"
    assert fake.calls == 1, "超时不该被重抛一次"


def test_from_image_bad_output_becomes_invalid_image(client, db, token_and_user, monkeypatch) -> None:
    """模型吐回的不是题目 JSON：对用户就是"这张图认不出来"，别丢内部措辞。

    坏输出允许重试 1 次（05 §7.0），所以这里断言打了 2 次才终态。
    """
    token, _ = token_and_user
    image_path = upload(client, token, image_bytes(600, 500)).json()["image_path"]

    class ChatterClient:
        def __init__(self):
            self.calls = 0

        def complete(self, operation, messages):
            from app.ai.client import LLMResponse

            self.calls += 1
            return LLMResponse(text="抱歉，我看不到题目", model="fake",
                               prompt_tokens=1, completion_tokens=1, latency_ms=1)

    fake = ChatterClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    resp = _extract(client, token, image_path)
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "AI_INVALID_IMAGE"
    assert fake.calls == 2

    with db() as s:
        log = s.scalars(select(AiCallLog).where(AiCallLog.status == "error")).all()[-1]
        assert log.error_code == "AI_INVALID_IMAGE"
        assert "看不到题目" in (log.raw_response or "")  # 原文要留着，否则没法定位


def test_from_image_truncated_output_tells_the_user_to_crop(
    client, db, token_and_user, monkeypatch
) -> None:
    """顶到 max_tokens 的图：文案要给出"裁小一点再来"这个动作，而不是 AI_INVALID_OUTPUT。

    实测依据：真实教材照片 4 道题 = 6776 输出 token（上限 8000），一页更密的确实会顶格。
    """
    token, _ = token_and_user
    image_path = upload(client, token, image_bytes(600, 500)).json()["image_path"]

    class TruncatingClient:
        def __init__(self):
            self.calls = 0

        def complete(self, operation, messages):
            from app.ai.client import LLMResponse

            self.calls += 1
            return LLMResponse(text='{"questions": [{"index": 1', model="fake",
                               prompt_tokens=10, completion_tokens=8000, latency_ms=1000,
                               finish_reason="length")

    fake = TruncatingClient()
    monkeypatch.setattr(extraction_service, "_llm_client", lambda: fake)
    resp = _extract(client, token, image_path)
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "AI_INVALID_IMAGE"
    assert "裁" in resp.json()["detail"]["message"]
    assert fake.calls == 1, "截断重试只会再截断一次，白等 35s"


def test_from_image_validates_request_shape(client, db, token_and_user) -> None:
    token, _ = token_and_user
    resp = client.post("/api/v1/questions/from-image", json={"image_path": ""},
                       headers=auth_headers(token))
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_vision_prompt_puts_the_data_guard_next_to_the_image(client, db) -> None:
    """05 §9.4：注入防线要贴在数据旁边——多模态请求里 system 离图片太远。"""
    from app.ai import prompts

    messages = prompts.vision_messages("data:image/jpeg;base64,AAA", "线性代数")
    assert [m["role"] for m in messages] == ["system", "user"]
    user_content = messages[1]["content"]
    assert isinstance(user_content, list) and len(user_content) == 2
    text_part = user_content[0]["text"]
    assert "线性代数" in text_part and "数据" in text_part and "指令" in text_part
    assert user_content[1]["type"] == "image_url"


def test_queue_path_still_logs_after_the_ai_log_refactor(client, db) -> None:
    """识图复用了 ai_call_logs 的写入口，队列那条路不能被重构写坏。"""
    token = register_user(client)["access_token"]
    resp = client.post(
        "/api/v1/questions",
        json={"subject": "高等数学", "question_type": "solve", "content_md": "求 $f(x)=x^2$ 的极小值。"},
        headers=auth_headers(token),
    )
    task_id = resp.json()["task_id"]
    task_worker.execute_task(db, task_id)
    with db() as s:
        log = s.scalars(select(AiCallLog)).all()[-1]
        assert log.operation == "analysis" and log.status == "success"
        assert log.queue_wait_ms is not None  # 任务侧才有的排队时长，识图那条是 None
