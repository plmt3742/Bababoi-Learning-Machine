"""任务队列与生成链路测试（BE-006/007 + ADR-006 三段并发）。

worker 不起真线程：直接调同步函数（claim / execute），用 FakeClient 替身控制输出。
"""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.ai.client import MockLLMClient
from app.core.config import settings
from app.db.base import utcnow
from app.models import AiCallLog, GeneratedQuestion, GenerationTask, Question
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


def _generate(client, token: str, qid: int, **body) -> list[dict]:
    """生题入队，返回 tasks[]（14 号 D1：不再有单个 task_id）。"""
    resp = client.post(
        f"/api/v1/questions/{qid}/generate", json=body, headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["tasks"]


def _generated_rows(db, qid: int, alive_only: bool = True) -> list[GeneratedQuestion]:
    with db() as s:
        stmt = select(GeneratedQuestion).where(GeneratedQuestion.parent_question_id == qid)
        if alive_only:
            stmt = stmt.where(GeneratedQuestion.deleted_at.is_(None))
        return list(s.scalars(stmt.order_by(GeneratedQuestion.target_index)))


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


def test_generate_enqueues_three_segments(client, db) -> None:
    """ADR-006：点一次"生成 3 道同类题"= 排 3 段任务，各带自己的格位与难度档。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]

    tasks = _generate(client, token, qid)
    assert [(t["target_index"], t["difficulty"]) for t in tasks] == [
        (1, "easy"), (2, "medium"), (3, "hard")
    ]
    assert len({t["task_id"] for t in tasks}) == 3
    with db() as s:
        rows = list(s.scalars(select(GenerationTask).where(GenerationTask.stage == "quiz")))
        assert all(r.target_index and r.difficulty for r in rows)


def test_difficulties_can_be_overridden_per_segment(client, db) -> None:
    """14 号 Q1：接口收 difficulties（自定义档位，允许三段同档），UI 暂时不接。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    tasks = _generate(client, token, qid, difficulties=["medium", "medium", "medium"])
    assert [t["difficulty"] for t in tasks] == ["medium"] * 3


@pytest.mark.parametrize(
    "body",
    [
        {"difficulty": "easy"},  # 整组只给一个档：语义不明，拒
        {"difficulties": ["easy"]},  # 整组要给 3 个
        {"target_index": 2, "difficulties": ["easy", "medium", "hard"]},  # 单段不该给列表
        {"target_index": 4},  # 只有三段
        {"difficulties": ["easy", "medium", "extreme"]},  # 档位不在码表里
    ],
)
def test_generate_rejects_bad_request_shape(client, db, body) -> None:
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    resp = client.post(
        f"/api/v1/questions/{qid}/generate", json=body, headers=auth_headers(token)
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_single_segment_enqueue_only_touches_that_slot(client, db) -> None:
    """14 号 Q4：单段重排收 target_index + difficulty，不能顺手把另外两段也排上。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    tasks = _generate(client, token, qid, target_index=3, difficulty="hard")
    assert len(tasks) == 1
    assert (tasks[0]["target_index"], tasks[0]["difficulty"]) == (3, "hard")


def test_three_segments_fill_three_slots_in_order(client, db, fake_llm) -> None:
    """每段成功只写自己那一格；三段跑完详情页正好三张卡。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]

    for task in _generate(client, token, qid):
        task_worker.execute_task(db, task["task_id"])

    detail = client.get(
        f"/api/v1/questions/{qid}?include=generated", headers=auth_headers(token)
    ).json()
    cards = detail["generated_questions"]
    assert [c["target_index"] for c in cards] == [1, 2, 3]
    assert [c["difficulty"] for c in cards] == ["easy", "medium", "hard"]
    assert [c["question_type"] for c in cards] == ["blank", "solve", "choice"]
    for card in cards:
        assert card["model"] == "mock"
        assert card["prompt_version"] == "generate_v2"


def test_one_segment_failing_keeps_the_other_two(client, db, fake_llm) -> None:
    """14 号 P11 / Q6：一段失败不影响其余两段，失败那格可以单独重试。"""

    class OnlySlot3Broken:
        def __init__(self, inner):
            self.inner = inner

        def complete(self, operation, messages):
            if "第 3 道" in messages[-1]["content"]:
                from app.ai.errors import AIInvalidOutputError

                raise AIInvalidOutputError("这一段输出烂了")
            return self.inner.complete(operation, messages)

    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    tasks = _generate(client, token, qid)
    for task in tasks[:2]:
        task_worker.execute_task(db, task["task_id"])

    fake_llm["client"] = OnlySlot3Broken(MockLLMClient())
    task_worker.execute_task(db, tasks[2]["task_id"])  # 第 3 段：失败 → requeue
    task_worker.execute_task(db, tasks[2]["task_id"])  # 重试仍失败 → failed

    with db() as s:
        third = s.get(GenerationTask, tasks[2]["task_id"])
        assert third.status == "failed"
        assert third.target_index == 3 and third.difficulty == "hard"
    alive = _generated_rows(db, qid)
    assert [row.target_index for row in alive] == [1, 2]  # 前两段的成果没被牵连

    # 单段重试：只补第 3 格
    fake_llm["client"] = MockLLMClient()
    resp = client.post(f"/api/v1/tasks/{tasks[2]['task_id']}/retry", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    task_worker.execute_task(db, tasks[2]["task_id"])
    assert [row.target_index for row in _generated_rows(db, qid)] == [1, 2, 3]


def test_group_regenerate_soft_deletes_old_group_on_enqueue(client, db, fake_llm) -> None:
    """14 号 Q2-A：整组重生成入队即软删旧组（产品接受"生成中看不到旧组"）。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    for task in _generate(client, token, qid):
        task_worker.execute_task(db, task["task_id"])
    assert len(_generated_rows(db, qid)) == 3

    _generate(client, token, qid)  # 只入队，一段都还没跑
    assert _generated_rows(db, qid) == []
    # 软删不物理删：practice_records 的外键还要指回这些行
    assert len(_generated_rows(db, qid, alive_only=False)) == 3


def test_single_segment_regenerate_keeps_other_slots(client, db, fake_llm) -> None:
    """单段重生成不许删整组——那是另外两段刚写好的成果。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    for task in _generate(client, token, qid):
        task_worker.execute_task(db, task["task_id"])

    retry = _generate(client, token, qid, target_index=2, difficulty="medium")
    task_worker.execute_task(db, retry[0]["task_id"])

    alive = _generated_rows(db, qid)
    assert [row.target_index for row in alive] == [1, 2, 3]
    # 只有第 2 格留了历史行：替换发生在同一格内
    history = [row for row in _generated_rows(db, qid, alive_only=False) if row.deleted_at]
    assert [row.target_index for row in history] == [2]


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


def test_requeue_stops_after_requeue_deadline(client, db, fake_llm) -> None:
    """14 号 D8：跑了 90s 以上的段不再自动重排，直接终态，免得用户干等第二轮。"""
    from app.ai.errors import AIInvalidOutputError

    class BrokenClient:
        def complete(self, operation, messages):
            raise AIInvalidOutputError("超时了")

    fake_llm["client"] = BrokenClient()
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    task_id = _generate(client, token, qid)[0]["task_id"]

    with db() as s:
        task = s.get(GenerationTask, task_id)
        task.status = "running"
        task.started_at = utcnow() - timedelta(seconds=settings.task_requeue_deadline_s + 30)
        s.commit()

    task_worker.execute_task(db, task_id)

    with db() as s:
        task = s.get(GenerationTask, task_id)
        assert task.status == "failed"
        assert task.retry_index == 0  # 没排第二轮


def test_manual_retry_requeues_failed_task(client, db, fake_llm) -> None:
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    task_id = _generate(client, token, qid)[0]["task_id"]
    task_worker.execute_task(db, task_id)  # mock 正常输出

    with db() as s:
        assert s.get(GenerationTask, task_id).status == "done"

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


def test_enqueue_reuses_active_segment(client, db) -> None:
    """12号 §3.3：同一格只允许一个 active 任务；重复点生成不会排成 6 段。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]

    first = _generate(client, token, qid)
    second = _generate(client, token, qid)
    assert [t["task_id"] for t in first] == [t["task_id"] for t in second]


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


def _single(content_md: str, difficulty: str = "easy") -> str:
    return json.dumps({
        "question_type": "solve",
        "content_md": content_md,
        "answer_md": "略",
        "explanation_md": "略",
        "difficulty": difficulty,
    }, ensure_ascii=False)


def test_quiz_copying_original_question_is_rejected(client, db, fake_llm) -> None:
    """原题题干要传进段校验，否则「把原题抄一遍」这种输出能直接入库。"""
    token = register_user(client)["access_token"]
    body = _create_question(client, token)["question"]
    fake_llm["client"] = _ScriptedClient(_single(body["content_md"]))

    task_id = _generate(client, token, body["id"])[0]["task_id"]
    task_worker.execute_task(db, task_id)  # 第一次失败 → requeue
    task_worker.execute_task(db, task_id)  # 第二次仍失败 → failed

    with db() as s:
        task = s.get(GenerationTask, task_id)
        assert task.status == "failed"
        assert task.error_code == "AI_INVALID_OUTPUT"
        assert "原题逐字相同" in task.error_message
    assert _generated_rows(db, body["id"]) == []


def test_segment_rejects_copy_of_a_sibling(client, db, fake_llm) -> None:
    """ADR-006：同组其它段的题干也要参与查重——否则两段可以逐字相同（14 号 §2.1-3）。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    tasks = _generate(client, token, qid)
    task_worker.execute_task(db, tasks[0]["task_id"])  # 第 1 格先落库
    first_content = _generated_rows(db, qid)[0].content_md

    fake_llm["client"] = _ScriptedClient(_single(first_content, "medium"))
    task_worker.execute_task(db, tasks[1]["task_id"])
    task_worker.execute_task(db, tasks[1]["task_id"])

    with db() as s:
        task = s.get(GenerationTask, tasks[1]["task_id"])
        assert task.status == "failed"
        assert "同组其它段完全相同" in task.error_message
    assert [row.target_index for row in _generated_rows(db, qid)] == [1]  # 第 1 格不受影响


def test_write_back_failure_does_not_leave_task_running(client, db, fake_llm, monkeypatch) -> None:
    """落库异常也得有终态——任务停在 running 会白占并发位，重启前没人再碰它。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    task_id = _generate(client, token, qid)[0]["task_id"]

    def boom(*args, **kwargs):
        raise RuntimeError("库写不进去")

    monkeypatch.setattr(task_worker, "_apply_segment", boom)
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


def test_analysis_task_and_segment_do_not_dedupe_each_other(client, db) -> None:
    """去重键是 question+stage+target_index：analysis（NULL）和三段互不顶掉。"""
    from app.services import task_service

    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    with db() as s:
        group = task_service.enqueue_generation(s, 1, qid)
        analysis = task_service.enqueue(s, 1, qid, stage="analysis")
    assert len(group) == 3
    assert analysis.id not in {t.id for t in group}


def test_invalid_output_keeps_raw_text_in_call_log(client, db, fake_llm) -> None:
    """坏输出必须留在 ai_call_logs.raw_response，否则没法定位是 prompt 还是模型的问题。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    fake_llm["client"] = _ScriptedClient('{"questions": [{" nonsense": 1}]}')

    task_id = _generate(client, token, qid)[0]["task_id"]
    task_worker.execute_task(db, task_id)

    with db() as s:
        log = s.scalar(select(AiCallLog).where(AiCallLog.status == "error"))
        assert log is not None
        assert "nonsense" in (log.raw_response or "")
        assert log.error_code == "AI_INVALID_OUTPUT"


def test_analysis_fills_missing_answer_but_never_overwrites(client, db, fake_llm) -> None:
    """05 §7.1：answer_md/explanation_md 走 questions 正字段，且只在原题为空时补。"""
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


def test_generation_prompt_gets_knowledge_points_from_analysis(client, db, fake_llm) -> None:
    """三段并发的"同知识点"靠分析结果喂进去：分析跑完再生成，提示词里要有知识点。"""
    seen: list[str] = []

    class SpyClient:
        def complete(self, operation, messages):
            seen.append(messages[-1]["content"])
            return MockLLMClient().complete(operation, messages)

    token = register_user(client)["access_token"]
    body = _create_question(client, token)
    task_worker.execute_task(db, body["task_id"])  # 先跑分析
    fake_llm["client"] = SpyClient()
    quiz_tasks = _generate(client, token, body["question"]["id"])
    task_worker.execute_task(db, quiz_tasks[0]["task_id"])

    assert "单调性" in seen[-1]  # 分析出的知识点进了生成提示词


def test_task_out_exposes_slot_and_error_message(client, db, fake_llm) -> None:
    """任务中心要能显示"生题 2/3"和失败原因（14 号 Q7 / #6 补的 error_message）。"""
    token = register_user(client)["access_token"]
    qid = _create_question(client, token)["question"]["id"]
    tasks = _generate(client, token, qid)

    with db() as s:
        task = s.get(GenerationTask, tasks[1]["task_id"])
        task.status = "failed"
        task.error_code = "AI_INVALID_OUTPUT"
        task.error_message = "与原题高度重复"
        s.commit()

    items = client.get(f"/api/v1/tasks?question_id={qid}", headers=auth_headers(token)).json()["items"]
    quiz_items = {i["target_index"]: i for i in items if i["stage"] == "quiz"}
    assert sorted(quiz_items) == [1, 2, 3]
    assert quiz_items[2]["difficulty"] == "medium"
    assert quiz_items[2]["error_message"] == "与原题高度重复"
