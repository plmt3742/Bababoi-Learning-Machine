"""识图任务化（B 档）：提交 / 轮询 / 准入 / 领取 / 自愈。"""
from __future__ import annotations

import io
import threading
from datetime import timedelta

import pytest
from PIL import Image
from sqlalchemy import select

from app.ai.errors import AITimeoutError
from app.core.config import settings
from app.core.errors import ErrorCode
from app.db.base import utcnow
from app.models import VisionExtractCache, VisionJob
from app.services import extraction_service, vision_job_service, vision_worker
from tests.conftest import auth_headers, register_user


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (235, 235, 235)).save(buffer, "PNG")
    return buffer.getvalue()


def _upload(client, token: str) -> str:
    resp = client.post(
        "/api/v1/uploads/images",
        files={"file": ("crop.png", _image_bytes(), "image/png")},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["image_path"]


def _upload_shade(client, token: str, shade: int) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (shade, shade, shade)).save(buffer, "PNG")
    resp = client.post(
        "/api/v1/uploads/images",
        files={"file": (f"crop{shade}.png", buffer.getvalue(), "image/png")},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["image_path"]


def _user(client, username: str = "识图_01") -> tuple[str, int]:
    data = register_user(client, username)
    return data["access_token"], data["user"]["id"]


def _submit(client, token: str, image_path: str, **body):
    return client.post(
        "/api/v1/questions/from-image/jobs",
        json={"image_path": image_path, **body},
        headers=auth_headers(token),
    )


def _extract_sync(client, token: str, image_path: str):
    return client.post(
        "/api/v1/questions/from-image",
        json={"image_path": image_path},
        headers=auth_headers(token),
    )


def test_cache_hit_returns_result_without_creating_job(client, db) -> None:
    token, _ = _user(client)
    image_path = _upload(client, token)
    assert _extract_sync(client, token, image_path).status_code == 200

    resp = _submit(client, token, image_path)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["job_id"] is None and body["status"] == "done"
    assert body["result"]["questions"], "命中缓存要把结果直接带回来"
    with db() as session:
        assert session.scalar(select(VisionJob)) is None, "命中缓存不建行"


def test_submit_enqueues_and_polling_is_owner_scoped(client, db) -> None:
    token, user_id = _user(client)
    other = register_user(client, "识图_02")["access_token"]
    image_path = _upload(client, token)

    resp = _submit(client, token, image_path, force_refresh=True)
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]
    assert resp.json()["queue_position"] == 1

    owner = client.get(
        f"/api/v1/questions/from-image/jobs/{job_id}", headers=auth_headers(token)
    )
    assert owner.status_code == 200 and owner.json()["status"] == "queued"

    intruder = client.get(
        f"/api/v1/questions/from-image/jobs/{job_id}", headers=auth_headers(other)
    )
    assert intruder.status_code == 404, intruder.text
    assert intruder.json()["detail"]["code"] == str(ErrorCode.VISION_JOB_NOT_FOUND)

    with db() as session:
        job = session.get(VisionJob, job_id)
        assert job.user_id == user_id and job.active_slot == user_id


def test_same_params_reuse_and_different_params_reject(client, db) -> None:
    token, _ = _user(client)
    image_path = _upload(client, token)

    first = _submit(client, token, image_path, force_refresh=True)
    assert first.status_code == 202
    again = _submit(client, token, image_path, force_refresh=True)
    assert again.status_code == 202
    assert again.json()["job_id"] == first.json()["job_id"]
    assert again.json()["reused"] is True

    changed = _submit(client, token, image_path, subject="高等数学")
    assert changed.status_code == 429, changed.text
    assert changed.json()["detail"]["code"] == str(ErrorCode.VISION_PREVIOUS_PENDING)

    with db() as session:
        assert session.scalar(select(VisionJob)) is not None
        assert len(session.scalars(select(VisionJob)).all()) == 1


def test_queue_full_has_retry_after(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "vision_queue_max_depth", 0)
    token, _ = _user(client)
    image_path = _upload(client, token)

    resp = _submit(client, token, image_path, force_refresh=True)
    assert resp.status_code == 429, resp.text
    assert resp.json()["detail"]["code"] == str(ErrorCode.VISION_QUEUE_FULL)
    assert resp.headers.get("Retry-After") == "30"


def test_queue_full_by_wait_estimate(client, db, monkeypatch) -> None:
    """准入只看估算：给 32s 就拒（准入闸 30），判死闸 40 会放行——钉住用的是准入键。

    直接打桩 `_estimate_wait_s`，让「闸门用哪个键」和「公式怎么算」互不牵连。
    """
    token, _ = _user(client)
    image_path = _upload(client, token)
    monkeypatch.setattr(vision_job_service, "_estimate_wait_s", lambda session, ahead: 32)

    resp = _submit(client, token, image_path, force_refresh=True)
    assert resp.status_code == 429, resp.text
    assert resp.json()["detail"]["code"] == str(ErrorCode.VISION_QUEUE_FULL)
    assert resp.headers.get("Retry-After") == "30"


def test_admission_boundary_is_not_self_killed(client, db) -> None:
    """准入 30s 放进来、实际等了 39s 的任务：认领判死闸是 40s，不能判死。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)
    job_id = _make_queued(db, user_id, image_path, created_offset_s=39)

    with db() as session:
        claimed = vision_job_service.claim_next(session)
        assert claimed is not None and claimed.id == job_id
        assert claimed.status == "running" and claimed.attempts == 1


def test_claim_skips_queue_timeout_for_requeued_job(client, db) -> None:
    """自愈重排过的任务 attempts>=1：created_at 很旧也不能被判"排队太久"。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        job = VisionJob(
            user_id=user_id,
            image_path=image_path,
            status="queued",
            active_slot=user_id,
            attempts=1,
            created_at=now - timedelta(seconds=120),
            expires_at=now + timedelta(hours=24),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with db() as session:
        claimed = vision_job_service.claim_next(session)
        assert claimed is not None and claimed.id == job_id
        assert claimed.status == "running" and claimed.attempts == 2


def test_terminal_updates_ignore_non_running_job(client, db) -> None:
    """mark_done/mark_failed 只对 running 生效：不能把排队/已终态的行改坏。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)
    job_id = _make_queued(db, user_id, image_path)

    with db() as session:
        vision_job_service.mark_done(session, job_id, {"questions": []})
        vision_job_service.mark_failed(session, job_id, "INTERNAL_ERROR", "不该生效")
    with db() as session:
        job = session.get(VisionJob, job_id)
        assert job.status == "queued"
        assert job.error_code is None and job.result_json is None


def test_rejected_force_submit_does_not_consume_cooldown(client, db, monkeypatch) -> None:
    """准入拒绝发生在扣额度之前：否则按 Retry-After 重试会连吃两个 429。"""
    token, _ = _user(client)
    image_path = _upload(client, token)
    # 先同步识别一次，落一行缓存——强刷冷却只对已有缓存行生效
    assert _extract_sync(client, token, image_path).status_code == 200
    with db() as session:
        assert session.scalar(select(VisionExtractCache)).last_forced_at is None

    monkeypatch.setattr(settings, "vision_queue_max_depth", 0)
    blocked = _submit(client, token, image_path, force_refresh=True)
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["detail"]["code"] == str(ErrorCode.VISION_QUEUE_FULL)

    with db() as session:
        assert session.scalar(select(VisionExtractCache)).last_forced_at is None, (
            "被队列拒掉的请求不能消耗强刷冷却"
        )


def _make_queued(db, user_id: int, image_path: str, *, created_offset_s: int = 0) -> int:
    with db() as session:
        now = utcnow()
        job = VisionJob(
            user_id=user_id,
            image_path=image_path,
            status="queued",
            active_slot=user_id,
            created_at=now - timedelta(seconds=created_offset_s),
            expires_at=now + timedelta(hours=24),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def test_claim_is_fifo_and_exclusive(client, db) -> None:
    token, user_id = _user(client)
    image_path = _upload(client, token)
    first_id = _make_queued(db, user_id, image_path)
    # active_slot 唯一：第二个任务必须换个用户
    _make_queued(db, user_id + 999, image_path)

    with db() as session:
        claimed = vision_job_service.claim_next(session)
        assert claimed is not None and claimed.id == first_id
        assert claimed.status == "running" and claimed.attempts == 1
        # 同一任务不能再被领走（条件 UPDATE 后 rowcount=0）
        other = vision_job_service.claim_next(session)
        assert other is not None and other.id != first_id


def test_claim_fails_job_that_waited_too_long(client, db) -> None:
    token, user_id = _user(client)
    image_path = _upload(client, token)
    job_id = _make_queued(db, user_id, image_path, created_offset_s=120)

    with db() as session:
        assert vision_job_service.claim_next(session) is None
        job = session.get(VisionJob, job_id)
        assert job.status == "failed"
        assert job.error_code == str(ErrorCode.VISION_QUEUE_TIMEOUT)
        assert job.active_slot is None


def test_claim_fails_job_just_past_the_kill_line(client, db) -> None:
    """判死上界：41s 必须 failed（39s 的用例抓不到 `>` 被写成 `>=`）。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)
    job_id = _make_queued(db, user_id, image_path, created_offset_s=41)

    with db() as session:
        assert vision_job_service.claim_next(session) is None
        job = session.get(VisionJob, job_id)
        assert job.status == "failed"
        assert job.error_code == str(ErrorCode.VISION_QUEUE_TIMEOUT)


def test_execute_job_writes_result(client, db, monkeypatch) -> None:
    token, user_id = _user(client)
    image_path = _upload(client, token)
    job_id = _make_queued(db, user_id, image_path)

    monkeypatch.setattr(
        extraction_service,
        "extract_from_image",
        lambda *args, **kwargs: {
            "image_path": image_path,
            "questions": [],
            "warnings": [],
            "cached": False,
            "extracted_at": utcnow(),
        },
    )
    with db() as session:
        claimed = vision_job_service.claim_next(session)

    vision_worker.execute_job(db, claimed.id)

    with db() as session:
        job = session.get(VisionJob, job_id)
        assert job.status == "done"
        assert job.active_slot is None and job.result_json is not None
        assert job.finished_at is not None


def test_execute_job_marks_ai_timeout(client, db, monkeypatch) -> None:
    token, user_id = _user(client)
    image_path = _upload(client, token)
    job_id = _make_queued(db, user_id, image_path)
    with db() as session:
        claimed = vision_job_service.claim_next(session)

    def boom(*args, **kwargs):
        raise AITimeoutError("识图超时，请重试")

    monkeypatch.setattr(extraction_service, "extract_from_image", boom)
    vision_worker.execute_job(db, claimed.id)

    with db() as session:
        job = session.get(VisionJob, job_id)
        assert job.status == "failed"
        assert job.error_code == "AI_TIMEOUT"
        assert job.active_slot is None


def test_recover_stale_running_jobs(client, db) -> None:
    token, user_id = _user(client)
    other_id = register_user(client, "识图_99")["user"]["id"]
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        retry = VisionJob(
            user_id=user_id, image_path=image_path, status="running", attempts=1,
            active_slot=user_id, created_at=now, started_at=now - timedelta(seconds=600),
            expires_at=now + timedelta(hours=24),
        )
        dead = VisionJob(
            user_id=other_id, image_path=image_path, status="running", attempts=2,
            active_slot=other_id, created_at=now, started_at=now - timedelta(seconds=600),
            expires_at=now + timedelta(hours=24),
        )
        session.add_all([retry, dead])
        session.commit()
        retry_id, dead_id = retry.id, dead.id

    assert vision_job_service.recover_stale(db) == 2
    with db() as session:
        assert session.get(VisionJob, retry_id).status == "queued"
        assert session.get(VisionJob, dead_id).status == "failed"
        assert session.get(VisionJob, dead_id).active_slot is None


def test_recover_stale_running_sweep(client, db) -> None:
    """运行期自愈：deadline 过了 grace 还在 running 的行要处理，宽限期内不动。"""
    token, user_id = _user(client)
    other_id = register_user(client, "识图_95")["user"]["id"]
    live_id = register_user(client, "识图_94")["user"]["id"]
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        retry = VisionJob(
            user_id=user_id, image_path=image_path, status="running", attempts=1,
            active_slot=user_id, created_at=now, started_at=now - timedelta(seconds=200),
            deadline_at=now - timedelta(seconds=40),
            expires_at=now + timedelta(hours=24),
        )
        dead = VisionJob(
            user_id=other_id, image_path=image_path, status="running", attempts=2,
            active_slot=other_id, created_at=now, started_at=now - timedelta(seconds=200),
            deadline_at=now - timedelta(seconds=40),
            expires_at=now + timedelta(hours=24),
        )
        alive = VisionJob(
            user_id=live_id, image_path=image_path, status="running", attempts=1,
            active_slot=live_id, created_at=now, started_at=now,
            deadline_at=now + timedelta(seconds=100),
            expires_at=now + timedelta(hours=24),
        )
        session.add_all([retry, dead, alive])
        session.commit()
        retry_id, dead_id, alive_id = retry.id, dead.id, alive.id

    assert vision_job_service.recover_stale_running(db) == 2
    with db() as session:
        requeued = session.get(VisionJob, retry_id)
        assert requeued.status == "queued"
        assert requeued.attempts == 1 and requeued.deadline_at is None
        failed = session.get(VisionJob, dead_id)
        assert failed.status == "failed" and failed.active_slot is None
        assert session.get(VisionJob, alive_id).status == "running", "宽限期内不能动"


def test_force_resubmit_reuses_job_instead_of_cooldown(client, db) -> None:
    """双击"重新识别"：第二发落在冷却窗口里，应复用单号而不是 429。"""
    token, _ = _user(client)
    image_path = _upload(client, token)
    # 先同步识别一次，落缓存行——强刷冷却只对已有缓存行生效
    assert _extract_sync(client, token, image_path).status_code == 200

    first = _submit(client, token, image_path, force_refresh=True)
    assert first.status_code == 202, first.text
    again = _submit(client, token, image_path, force_refresh=True)
    assert again.status_code == 202, again.text
    assert again.json()["reused"] is True
    assert again.json()["job_id"] == first.json()["job_id"]


def test_conflict_returns_force_slot(client, db, monkeypatch) -> None:
    """入队撞 active_slot 唯一约束时，刚占的强刷额度要归还。"""
    token, user_id = _user(client)
    # 两张不同内容的图（同字节会被内容寻址归并成同一行缓存，测不出各自额度）
    image_a = _upload_shade(client, token, 235)
    image_b = _upload_shade(client, token, 120)
    assert _extract_sync(client, token, image_a).status_code == 200
    assert _extract_sync(client, token, image_b).status_code == 200
    # 先真实占一个 active 任务（另一张图），让第二次提交在 insert 时撞唯一约束
    assert _submit(client, token, image_a, force_refresh=True).status_code == 202

    real_active = vision_job_service._active_job
    calls = {"n": 0}

    def skip_first_precheck(session, uid):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # 跳过提交路径的"已有 active"预检，逼到 insert 冲突
        return real_active(session, uid)

    monkeypatch.setattr(vision_job_service, "_active_job", skip_first_precheck)

    resp = _submit(client, token, image_b, force_refresh=True)
    assert resp.status_code == 429, resp.text
    assert resp.json()["detail"]["code"] == str(ErrorCode.VISION_PREVIOUS_PENDING)
    with db() as session:
        rows = session.scalars(select(VisionExtractCache)).all()
        forced = [row for row in rows if row.last_forced_at is not None]
        assert len(forced) == 1, "输的一方要归还强刷额度，只有赢家占用冷却"


def test_concurrent_same_params_submit_creates_one_job(client, db) -> None:
    """4 线程同参并发：只落一行，其余全部 reused=True（不能有 500）。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)

    results: list[object] = [None] * 4

    def do_submit(index: int) -> None:
        with db() as session:
            try:
                results[index] = vision_job_service.submit(
                    session,
                    db,
                    user_id,
                    image_path=image_path,
                    subject=None,
                    force_refresh=False,
                )
            except Exception as exc:  # noqa: BLE001 失败也要带回主线程断言
                results[index] = exc

    threads = [threading.Thread(target=do_submit, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(isinstance(result, dict) for result in results), results
    job_ids = {result["job_id"] for result in results}
    assert len(job_ids) == 1
    assert sum(1 for result in results if result["reused"]) == 3
    with db() as session:
        assert len(session.scalars(select(VisionJob)).all()) == 1


def test_swept_running_job_can_be_claimed_and_finishes(client, db, monkeypatch) -> None:
    """自愈闭环：被清扫回队列的任务能再次认领并跑完，而不是立刻被判排队超时。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        job = VisionJob(
            user_id=user_id, image_path=image_path, status="running", attempts=1,
            active_slot=user_id, created_at=now - timedelta(seconds=200),
            started_at=now - timedelta(seconds=200),
            deadline_at=now - timedelta(seconds=40),
            expires_at=now + timedelta(hours=24),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    assert vision_job_service.recover_stale_running(db) == 1
    with db() as session:
        claimed = vision_job_service.claim_next(session)
    assert claimed is not None and claimed.id == job_id
    assert claimed.status == "running" and claimed.attempts == 2

    monkeypatch.setattr(
        extraction_service,
        "extract_from_image",
        lambda *args, **kwargs: {
            "image_path": image_path,
            "questions": [],
            "warnings": [],
            "cached": False,
            "extracted_at": utcnow(),
        },
    )
    vision_worker.execute_job(db, job_id)
    with db() as session:
        assert session.get(VisionJob, job_id).status == "done"


def test_settings_reject_vision_budget_violations() -> None:
    """预算不变量在 pydantic validator 里：构造 Settings 即校验，任何进程都拦得住。"""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="VISION_CALL_TIMEOUT_S"):
        Settings(_env_file=None, vision_call_timeout_s=140, vision_run_deadline_s=140)
    # 105 是硬边界本身（140−30−5），必须放行
    Settings(_env_file=None, vision_call_timeout_s=105, vision_run_deadline_s=140)
    with pytest.raises(ValidationError, match="VISION_RUN_DEADLINE_S"):
        Settings(_env_file=None, vision_run_deadline_s=141)


def test_cleanup_only_removes_expired_terminal(client, db) -> None:
    token, user_id = _user(client)
    other_id = register_user(client, "识图_98")["user"]["id"]
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        session.add_all(
            [
                VisionJob(
                    user_id=user_id, image_path=image_path, status="done",
                    created_at=now, expires_at=now - timedelta(minutes=1),
                ),
                VisionJob(
                    user_id=other_id, image_path=image_path, status="queued",
                    active_slot=other_id, created_at=now,
                    expires_at=now - timedelta(minutes=1),
                ),
            ]
        )
        session.commit()

    assert vision_job_service.cleanup_expired(db) == 1
    with db() as session:
        statuses = [job.status for job in session.scalars(select(VisionJob)).all()]
        assert statuses == ["queued"], "queued 的即使过期也不能删"


def test_admission_estimate_counts_running_jobs(client, db, monkeypatch) -> None:
    """准入估算要把正在跑的 worker 算进去，否则会放进来再被判排队超时。"""
    monkeypatch.setattr(settings, "vision_max_concurrency", 1)
    token, _ = _user(client)
    other_id = register_user(client, "识图_97")["user"]["id"]
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        session.add(
            VisionJob(
                user_id=other_id, image_path=image_path, status="running", attempts=1,
                active_slot=other_id, created_at=now, started_at=now,
                deadline_at=now + timedelta(seconds=140),
                expires_at=now + timedelta(hours=24),
            )
        )
        session.commit()

    resp = _submit(client, token, image_path, force_refresh=True)
    assert resp.status_code == 202, resp.text
    # 默认均值 25s、1 个 worker、前面 1 个 running → 估算 25s（旧算法会算成 1）
    assert resp.json()["estimated_wait_s"] == 25


def test_admission_runtime_average_has_floor(client, db) -> None:
    """均值会被小图拉低：准入宁可保守，不能按 12s 放人进来再判排队超时。"""
    token, user_id = _user(client)
    image_path = _upload(client, token)
    with db() as session:
        now = utcnow()
        for _ in range(3):
            session.add(
                VisionJob(
                    user_id=user_id,
                    image_path=image_path,
                    status="done",
                    started_at=now - timedelta(seconds=12),
                    finished_at=now,
                    created_at=now - timedelta(seconds=12),
                    expires_at=now + timedelta(hours=24),
                )
            )
        session.commit()
        assert vision_job_service._avg_runtime_seconds(session) == 20.0


def test_polling_queued_job_reports_position(client, db) -> None:
    """刷新页面后重新轮询也要能显示"前面还有几个"。"""
    token, _ = _user(client)
    other_id = register_user(client, "识图_96")["user"]["id"]
    image_path = _upload(client, token)
    _make_queued(db, other_id, image_path)

    resp = _submit(client, token, image_path, force_refresh=True)
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    poll = client.get(
        f"/api/v1/questions/from-image/jobs/{job_id}", headers=auth_headers(token)
    )
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] == "queued"
    assert body["queue_position"] == 2
    assert body["estimated_wait_s"] is not None and body["estimated_wait_s"] >= 1
