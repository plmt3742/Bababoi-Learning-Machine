"""错题 CRUD API 测试（BE-004 验收项：创建/列表/详情/更新/软删 + 筛选搜索 + 归属）。"""
from __future__ import annotations

from tests.conftest import auth_headers, register_user


def _choice_payload(**overrides) -> dict:
    payload = {
        "subject": "高等数学",
        "chapter": "导数与极值",
        "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
        "question_type": "choice",
        "answer_md": "极大值 $f(-1)=3$",
        "options": [
            {"label": "A", "content_md": "$-1$"},
            {"label": "B", "content_md": "$3$"},
        ],
        "tags": ["导数", "极值"],
    }
    payload.update(overrides)
    return payload


def _blank_payload(**overrides) -> dict:
    payload = {
        "subject": "线性代数",
        "content_md": "矩阵的秩为 ___。",
        "question_type": "blank",
        "blanks": [{"index": 1, "answer_md": "$2$"}],
    }
    payload.update(overrides)
    return payload


def _create(client, token: str, payload: dict) -> dict:
    resp = client.post("/api/v1/questions", json=payload, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_returns_question_and_queued_task(client) -> None:
    """05 §6.4：保存 + 自动入队 analysis，返回 {question, task_id}。"""
    token = register_user(client)["access_token"]
    body = _create(client, token, _choice_payload())

    question = body["question"]
    assert question["subject"] == "高等数学"
    assert question["mastery_status"] == "unmastered"
    assert [t["name"] for t in question["tags"]] == ["导数", "极值"]
    assert question["options"][0]["label"] == "A"
    assert "password_hash" not in question

    detail = client.get(
        f"/api/v1/questions/{question['id']}", headers=auth_headers(token)
    ).json()
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0]["stage"] == "analysis"
    assert detail["tasks"][0]["status"] == "queued"
    assert detail["tasks"][0]["id"] == body["task_id"]
    assert detail["generated_questions"] == []


def test_create_rejects_type_rule_violations(client) -> None:
    """选项字母乱序 / 空位数与答案数不符 / 题干为空，都要 400。"""
    token = register_user(client)["access_token"]
    bad_payloads = [
        # 第二个选项的 label 不是 B
        _choice_payload(options=[{"label": "A", "content_md": "$1$"}, {"label": "C", "content_md": "$2$"}]),
        # 空位数 2、答案只有 1 个
        _blank_payload(content_md="___ + ___ = 3", blanks=[{"index": 1, "answer_md": "$1$"}]),
        # 填空题题干里没有 ___
        _blank_payload(content_md="矩阵的秩为多少？"),
        # 题干空白
        _choice_payload(content_md="   "),
        # 未知题型
        _choice_payload(question_type="essay"),
    ]
    for payload in bad_payloads:
        resp = client.post("/api/v1/questions", json=payload, headers=auth_headers(token))
        assert resp.status_code == 400, payload
        assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_list_paginates_and_returns_excerpt_not_full_text(client) -> None:
    token = register_user(client)["access_token"]
    long_text = "很长的题干" * 60  # 远超 excerpt 上限
    for i in range(3):
        _create(client, token, _choice_payload(content_md=f"{long_text}（{i}）"))

    page = client.get(
        "/api/v1/questions?page=1&page_size=2", headers=auth_headers(token)
    ).json()
    assert page["total"] == 3
    assert page["page"] == 1
    assert page["page_size"] == 2
    assert len(page["items"]) == 2

    # 最新在前；excerpt 被截断且不含全文
    first = page["items"][0]
    assert first["excerpt"].endswith("…")
    assert len(first["excerpt"]) <= 101
    assert "content_md" not in first

    last_page = client.get(
        "/api/v1/questions?page=2&page_size=2", headers=auth_headers(token)
    ).json()
    assert len(last_page["items"]) == 1

    # page_size 超上限被拒
    resp = client.get("/api/v1/questions?page_size=101", headers=auth_headers(token))
    assert resp.status_code == 400


def test_list_filters_by_subject_tag_mastery_and_keyword(client) -> None:
    token = register_user(client)["access_token"]
    _create(client, token, _choice_payload())  # 高等数学 / 导数、极值
    _create(client, token, _blank_payload())  # 线性代数
    _create(
        client,
        token,
        _choice_payload(subject="线性代数", content_md="含 100% 浓度的题干", tags=[]),
    )

    headers = auth_headers(token)
    assert (
        len(client.get("/api/v1/questions?subject=高等数学", headers=headers).json()["items"])
        == 1
    )
    assert (
        len(client.get("/api/v1/questions?tag=导数", headers=headers).json()["items"]) == 1
    )
    assert (
        len(
            client.get(
                "/api/v1/questions?mastery_status=unmastered", headers=headers
            ).json()["items"]
        )
        == 3
    )
    # q 命中题干关键字
    assert len(client.get("/api/v1/questions?q=极值", headers=headers).json()["items"]) == 1
    # q 里的 % 是字面字符，不当通配符
    assert (
        len(client.get("/api/v1/questions?q=100%25", headers=headers).json()["items"])
        == 1
    )
    assert client.get("/api/v1/questions?q=不存在词", headers=headers).json()["total"] == 0


def test_patch_updates_fields_tags_and_analysis(client) -> None:
    token = register_user(client)["access_token"]
    question = _create(client, token, _choice_payload())["question"]

    resp = client.patch(
        f"/api/v1/questions/{question['id']}",
        json={
            "answer_md": "选 B",
            "tags": ["导数"],
            "analysis": {
                "topic_type": "导数与极值",
                "difficulty": "medium",
                "knowledge_points": ["导数"],
                "error_reasons": ["未判断符号"],
                "solution_summary": "求导后列表判符号",
            },
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["answer_md"] == "选 B"
    assert [t["name"] for t in updated["tags"]] == ["导数"]
    assert updated["analysis"]["difficulty"] == "medium"

    # 题干也能改；改完仍是合法的 choice
    resp = client.patch(
        f"/api/v1/questions/{question['id']}",
        json={"content_md": "求函数 $f(x)=x^2$ 的最小值。"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["content_md"].startswith("求函数")


def test_patch_blank_question_content_breaking_markers_is_rejected(client) -> None:
    """填空题改题干后空位数变了 → 400，不允许库里出现标记与答案数不符的题。"""
    token = register_user(client)["access_token"]
    question = _create(client, token, _blank_payload())["question"]

    resp = client.patch(
        f"/api/v1/questions/{question['id']}",
        json={"content_md": "两个空：___ 和 ___。"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_soft_delete_hides_from_list_and_detail(client) -> None:
    token = register_user(client)["access_token"]
    question = _create(client, token, _choice_payload())["question"]
    qid = question["id"]

    resp = client.delete(f"/api/v1/questions/{qid}", headers=auth_headers(token))
    assert resp.status_code == 204

    detail = client.get(f"/api/v1/questions/{qid}", headers=auth_headers(token))
    assert detail.status_code == 404
    assert detail.json()["detail"]["code"] == "QUESTION_NOT_FOUND"
    assert client.get("/api/v1/questions", headers=auth_headers(token)).json()["total"] == 0

    # 再删一次也是 404（已软删的等于不存在）
    assert (
        client.delete(f"/api/v1/questions/{qid}", headers=auth_headers(token)).status_code
        == 404
    )


def test_ownership_is_enforced(client) -> None:
    """US-6：接口层校验归属——别人的题 403，不存在的题 404。"""
    token_a = register_user(client, "alice")["access_token"]
    token_b = register_user(client, "bob")["access_token"]
    qid = _create(client, token_a, _choice_payload())["question"]["id"]

    assert (
        client.get(f"/api/v1/questions/{qid}", headers=auth_headers(token_b)).status_code
        == 403
    )
    resp = client.get(f"/api/v1/questions/{qid}", headers=auth_headers(token_b))
    assert resp.json()["detail"]["code"] == "QUESTION_FORBIDDEN"
    assert (
        client.patch(
            f"/api/v1/questions/{qid}", json={"answer_md": "x"}, headers=auth_headers(token_b)
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/questions/{qid}", headers=auth_headers(token_b)).status_code
        == 403
    )
    # b 的列表里看不到 a 的题
    assert client.get("/api/v1/questions", headers=auth_headers(token_b)).json()["total"] == 0
    # 不存在的 id → 404
    missing = client.get("/api/v1/questions/99999", headers=auth_headers(token_a))
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "QUESTION_NOT_FOUND"


def test_questions_require_auth(client) -> None:
    resp = client.post("/api/v1/questions", json=_choice_payload())
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"

    resp = client.get("/api/v1/questions")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_search_matches_tag_name_not_only_content(client) -> None:
    """PRD 的搜索范围是「题干 + 知识点标签」：题干里没有关键词、标签里有，也要命中。"""
    token = register_user(client)["access_token"]
    _create(client, token, _choice_payload(tags=["洛朗展开"]))
    hit = client.get("/api/v1/questions", params={"q": "洛朗"}, headers=auth_headers(token))
    assert hit.json()["total"] == 1

    miss = client.get("/api/v1/questions", params={"q": "不存在词"}, headers=auth_headers(token))
    assert miss.json()["total"] == 0


def test_search_returns_each_question_once_with_multiple_tags(client) -> None:
    """一题挂两个都命中的标签时不能出现两行——所以搜索用 EXISTS 子查询而不是 join。"""
    token = register_user(client)["access_token"]
    _create(client, token, _choice_payload(tags=["极值", "极值点"]))
    page = client.get("/api/v1/questions", params={"q": "极值"}, headers=auth_headers(token)).json()
    assert page["total"] == 1
    assert len(page["items"]) == 1


def test_content_md_over_5000_rejected(client) -> None:
    """05 §5.2：题干 ≤5000 字符。"""
    token = register_user(client)["access_token"]
    resp = client.post(
        "/api/v1/questions",
        json=_choice_payload(content_md="x" * 5001),
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_patch_mastery_status_roundtrip(client) -> None:
    """确认单 B-5：掌握状态走 PATCH，前端自评后顺手改；后端不自动流转。"""
    token = register_user(client)["access_token"]
    qid = _create(client, token, _choice_payload())["question"]["id"]

    resp = client.patch(
        f"/api/v1/questions/{qid}",
        json={"mastery_status": "reviewing"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["mastery_status"] == "reviewing"

    # 能改就能按新状态筛出来
    page = client.get(
        "/api/v1/questions", params={"mastery_status": "reviewing"}, headers=auth_headers(token)
    ).json()
    assert page["total"] == 1

    bad = client.patch(
        f"/api/v1/questions/{qid}",
        json={"mastery_status": "已掌握"},
        headers=auth_headers(token),
    )
    assert bad.status_code == 400

