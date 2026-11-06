"""任务队列与生成链路测试（BE-006/007）。

worker 不起真线程：直接调同步函数（claim / execute），用 FakeClient 替身控制输出。
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai.client import MockLLMClient
from app.models import AiCallLog, GenerationTask, Question
from app.services import task_worker
from tests.conftest import auth_headers, register_user


@pytest.fixture()
def fake_llm(monkeypatch):
    """把 worker 的 LLM 客户端换成可编程替身。"""
    holder = {"client": MockLLMClient()}
    monkeypatch.setattr(task_worker, "_llm_client", lambda: holder["client"])
    return holder


def _create_question(client, token: str, payload: dict | None = None) -> dict:
    body = payload or {
        "subject": "高等数学",
        "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
        "question_type": "solve",
        "tags": ["导数"],
    }
    resp = client.post("/api/v1/questions", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_question_already_enqueues_analysis_task(client, db) -> None:
    """BE-004 的契约：保存错题后 analysis 任务已经在队列里。"""
    token = register_user(client)["access_token"]
    _create_question(client, token)
    with db() as s:
        tasks = list(s.scalars(select(GenerationTask)))
    assert len(tasks) == 1
    assert tasks[0].stage == "analysis"
    assert tasks[0].status == "queued"


def test_worker_executes_analysis_and_writes_back(client, db, fake_llm) -> None:
    token = register_user(client)["access_token"]
    question = _create_question(client, token)["question"]

    with db() as s:
        task_id = s.scalar(select(GenerationTask.id))
    task_worker.execute_task(db, task_id)

    with db() as s:
        task = s.get(GenerationTask, task_id)
        assert task.status == "done"
        q = s.get(Question, question["id"])
        assert q.analysis["topic_type"] == "导数与极值"
        assert {t.name for t in q.tags} >= {"导数", "极值", "单调性"}
        # ai_call_logs 落库（05 §9.3 独立事务）
        log = s.scalar(select(AiCallLog))
        assert log is not None
        assert log.operation == "analysis"
        assert log.status == "success"
        assert log.prompt_version == "analyze_v1"


def test_worker_executes_quiz_and_inserts_exactly_three(client, db, fake_llm) -> None:
    token = register_user(client)["access_token"]
    question = _create_question(client, token)["question"]

    resp = client.post(
        f"/api/v1/questions/{question['id']}/generate", headers=auth_headers(token)
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    task_worker.execute_task(db, task_id)

    detail = client.get(
        f"/api/v1/questions/{question['id']}?include=generated",
        headers=auth_headers(token),
    ).json()
    assert len(detail["generated_questions"]) == 3
    types = {g["question_type"] for g in detail["generated_questions"]}
    assert types == {"solve"}
    for generated in detail["generated_questions"]:
        assert generated["model"] == "mock"
        assert generated["prompt_version"] == "generate_v2"


def test_worker_retries_once_then_fails(client, db, fake_llm) -> None:
    """12号 §3.2：失败重试 1 次（requeue 后再执行），仍失败置 failed 并带错误码。"""
    from app.ai.errors import AIInvalidOutputError

    class BrokenClient:
        def __init__(self):
            self.calls = 0

        def complete(self, operation, messages):
            self.calls += 1
            raise AIInvalidOutputError("输出烂了")

    fake_llm["client"] = BrokenClient()
    token = register_user(client)["access_token"]
    _create_question(client, token)["question"]
    with db() as s:
        task_id = s.scalar(select(GenerationTask.id))

    # 第一次执行失败 → requeue；第二次执行仍失败 → failed（共 2 次 LLM 调用）
    task_worker.execute_task(db, task_id)
    task_worker.execute_task(db, task_id)

    with db() as s:
        task = s.get(GenerationTask, task_id)
        assert task.status == "failed"
        assert task.error_code == "AI_INVALID_OUTPUT"
        assert task.retry_index == 1
        assert fake_llm["client"].calls == 2
        assert task.error_message


def test_manual_retry_requeues_failed_task(client, db, fake_llm) -> None:
    token = register_user(client)["access_token"]
    _create_question(client, token)["question"]
    with db() as s:
        task_id = s.scalar(select(GenerationTask.id))
    task_worker.execute_task(db, task_id)  # BrokenClient 上一测试的替身已还原

    with db() as s:
        assert s.get(GenerationTask, task_id).status == "done"  # mock 正常输出

    # 手动把任务改成 failed 再 retry（模拟任务中心操作）
    with db() as s:
        task = s.get(GenerationTask, task_id)
        task.status = "failed"
        task.error_code = "AI_TIMEOUT"
        s.commit()

    resp = client.post(f"/api/v1/tasks/{task_id}/retry", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    # 对成功任务 retry 会被拒
    with db() as s:
        s.get(GenerationTask, task_id).status = "done"
        s.commit()
    resp = client.post(f"/api/v1/tasks/{task_id}/retry", headers=auth_headers(token))
    assert resp.status_code == 400


def test_enqueue_reuses_active_task(client, db) -> None:
    """12号 §3.3：同一 question+stage 只允许一个 active 任务。"""
    token = register_user(client)["access_token"]
    question = _create_question(client, token)["question"]

    first = client.post(
        f"/api/v1/questions/{question['id']}/generate", headers=auth_headers(token)
    ).json()["task_id"]
    second = client.post(
        f"/api/v1/questions/{question['id']}/generate", headers=auth_headers(token)
    ).json()["task_id"]
    assert first == second


def test_task_list_filters_and_ownership(client, db) -> None:
    token_a = register_user(client, "alice")["access_token"]
    token_b = register_user(client, "bob")["access_token"]
    question = _create_question(client, token_a)["question"]

    items = client.get(
        f"/api/v1/tasks?question_id={question['id']}", headers=auth_headers(token_a)
    ).json()["items"]
    assert len(items) == 1 and items[0]["stage"] == "analysis"

    # b 看不到 a 的任务
    assert (
        client.get("/api/v1/tasks", headers=auth_headers(token_b)).json()["items"] == []
    )
    # b 也不能 retry a 的任务
    with db() as s:
        task_id = s.scalar(select(GenerationTask.id))
    resp = client.post(f"/api/v1/tasks/{task_id}/retry", headers=auth_headers(token_b))
    assert resp.status_code == 403


def test_claim_next_is_atomic_under_contention(db, monkeypatch) -> None:
    """条件 UPDATE 抢占：第二个 claim 拿不到同一任务。"""
    with db() as s:
        s.add(GenerationTask(question_id=1, user_id=1, stage="analysis", status="queued"))
        s.commit()

    with db() as s1, db() as s2:
        first = task_worker._claim_next(s1)
        second = task_worker._claim_next(s2)
    assert first is not None
    assert second is None  # 同一个任务不能被领两次


class _ScriptedClient:
    """固定返回同一段文本的 LLM 替身。"""

    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, operation, messages):
        from app.ai.client import LLMResponse

        return LLMResponse(
            text=self.text, model="fake", prompt_tokens=1, completion_tokens=1, latency_ms=1
        )


def test_second_generate_keeps_exactly_three_questions(client, db, fake_llm) -> None:
    """重新生成整组是替换不是追加：详情页的「3 张题卡」不能变 6 张。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    from app.models import GeneratedQuestion

    for _ in range(2):
        task_id = client.post(
            f"/api/v1/questions/{qid}/generate", headers=auth_headers(token)
        ).json()["task_id"]
        task_worker.execute_task(db, task_id)

    detail = client.get(
        f"/api/v1/questions/{qid}?include=generated", headers=auth_headers(token)
    ).json()
    assert len(detail["generated_questions"]) == 3
    with db() as s:
        total = len(list(s.scalars(select(GeneratedQuestion))))
        alive = len(list(s.scalars(select(GeneratedQuestion).where(GeneratedQuestion.deleted_at.is_(None)))))
    assert (total, alive) == (6, 3)  # 旧组软删留痕，practice_records 的外键不悬空


def test_quiz_copying_original_question_is_rejected(client, db, fake_llm) -> None:
    """原题题干要传进生成校验，否则「把原题抄一遍」这种输出能直接入库。"""
    import json

    token = register_user(client)["access_token"]
    body = _create_question(client, token)["question"]
    copied = {
        "questions": [
            {
                "question_type": "solve",
                "content_md": body["content_md"],
                "answer_md": "略",
                "explanation_md": "略",
                "difficulty": "easy",
            }
        ]
        * 3
    }
    fake_llm["client"] = _ScriptedClient(json.dumps(copied, ensure_ascii=False))

    task_id = client.post(
        f"/api/v1/questions/{body['id']}/generate", headers=auth_headers(token)
    ).json()["task_id"]
    task_worker.execute_task(db, task_id)  # 第一次失败 → requeue
    task_worker.execute_task(db, task_id)  # 第二次仍失败 → failed

    with db() as s:
        task = s.get(GenerationTask, task_id)
        assert task.status == "failed"
        assert task.error_code == "AI_INVALID_OUTPUT"
        assert "原题高度重复" in task.error_message


def test_write_back_failure_does_not_leave_task_running(client, db, fake_llm, monkeypatch) -> None:
    """落库异常也得有终态——任务停在 running 会白占并发位，重启前没人再碰它。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    task_id = client.post(
        f"/api/v1/questions/{qid}/generate", headers=auth_headers(token)
    ).json()["task_id"]

    def boom(*args, **kwargs):
        raise RuntimeError("库写不进去")

    monkeypatch.setattr(task_worker, "_apply_quiz", boom)
    task_worker.execute_task(db, task_id)

    with db() as s:
        task = s.get(GenerationTask, task_id)
        assert task.status == "queued"  # 走 requeue，不是 running
        assert task.retry_index == 1
        assert task.error_code == "INTERNAL_ERROR"


def test_missing_task_uses_task_not_found(client, db) -> None:
    """05 §6.2 早就有 TASK_NOT_FOUND，别再拿通用的 NOT_FOUND 顶。"""
    token = register_user(client)["access_token"]
    resp = client.post("/api/v1/tasks/99999/retry", headers=auth_headers(token))
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TASK_NOT_FOUND"


def test_enqueue_dedupe_key_includes_target_index(client, db) -> None:
    """整组任务（target_index=NULL）和单题任务（1/2/3）不能互相顶掉。"""
    from app.services import task_service

    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    with db() as s:
        group = task_service.enqueue(s, 1, qid, stage="quiz")
        single = task_service.enqueue(s, 1, qid, stage="quiz", target_index=2)
    assert group.id != single.id
    assert single.target_index == 2


def test_invalid_output_keeps_raw_text_in_call_log(client, db, fake_llm) -> None:
    """坏输出必须留在 ai_call_logs.raw_response，否则没法定位是 prompt 还是模型的问题。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    fake_llm["client"] = _ScriptedClient('{"questions": [{" nonsense": 1}]}')

    task_id = client.post(
        f"/api/v1/questions/{qid}/generate", headers=auth_headers(token)
    ).json()["task_id"]
    task_worker.execute_task(db, task_id)

    with db() as s:
        log = s.scalar(select(AiCallLog).where(AiCallLog.status == "error"))
        assert log is not None
        assert "nonsense" in (log.raw_response or "")
        assert log.error_code == "AI_INVALID_OUTPUT"


def test_analysis_fills_missing_answer_but_never_overwrites(client, db, fake_llm) -> None:
    """05 §7.1：answer_md/explanation_md 走 questions 正字段，且只在原题为空时补。"""
    from app.models import Question

    token = register_user(client)["access_token"]

    # 1) 原题没填答案 → 分析后补上
    blank_q = client.post(
        "/api/v1/questions",
        json={
            "subject": "高等数学",
            "question_type": "solve",
            "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
        },
        headers=auth_headers(token),
    ).json()
    task_worker.execute_task(db, blank_q["task_id"])
    with db() as s:
        q = s.get(Question, blank_q["question"]["id"])
        assert q.answer_md == "极大值 $f(-1)=3$，极小值 $f(1)=-1$"
        assert q.explanation_md
        # analysis JSON 里不再重复存这两个字段
        assert "answer_md" not in q.analysis
        assert "explanation_md" not in q.analysis

    # 2) 原题已填答案 → 保留用户写的
    filled = client.post(
        "/api/v1/questions",
        json={
            "subject": "高等数学",
            "question_type": "solve",
            "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
            "answer_md": "我自己算的：极大值 3",
            "explanation_md": "我自己写的解析",
        },
        headers=auth_headers(token),
    ).json()
    task_worker.execute_task(db, filled["task_id"])
    with db() as s:
        q = s.get(Question, filled["question"]["id"])
        assert q.answer_md == "我自己算的：极大值 3"
        assert q.explanation_md == "我自己写的解析"


def test_analysis_merges_tags_instead_of_replacing_them(client, db, fake_llm) -> None:
    """AI 知识点是追加：用户手动打的标签不能被分析冲掉（#5 review 阻塞 2）。"""
    from app.models import Question

    token = register_user(client)["access_token"]
    body = _create_question(client, token, {
        "subject": "高等数学",
        "question_type": "solve",
        "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
        "tags": ["我的易错", "导数"],
    })
    task_worker.execute_task(db, body["task_id"])

    with db() as s:
        names = {t.name for t in s.get(Question, body["question"]["id"]).tags}
    assert "我的易错" in names  # 用户的手动标签还在
    assert "导数" in names  # 与 AI 知识点重名的不重复
    assert {"极值", "单调性"} <= names  # AI 知识点已追加


def test_task_out_exposes_error_message(client, db, fake_llm) -> None:
    """任务中心要能显示失败原因，只有 error_code 就得让前端硬背码表。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    task_id = client.post(
        f"/api/v1/questions/{qid}/generate", headers=auth_headers(token)
    ).json()["task_id"]

    with db() as s:
        task = s.get(GenerationTask, task_id)
        task.status = "failed"
        task.error_code = "AI_INVALID_OUTPUT"
        task.error_message = "第 2 题与原题高度重复"
        s.commit()

    items = client.get("/api/v1/tasks", params={"question_id": qid}, headers=auth_headers(token)).json()["items"]
    assert items[0]["error_message"] == "第 2 题与原题高度重复"
