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


def _valid_analysis(**overrides) -> dict:
    """05 §7.1 的合法 analysis；answer_md/explanation_md 必填。"""
    payload = {
        "topic_type": "导数与极值",
        "difficulty": "medium",
        "knowledge_points": ["导数"],
        "error_reasons": ["未判断符号"],
        "answer_md": "极大值 $f(-1)=3$",
        "explanation_md": "求导后判符号。",
        "solution_summary": "求导后列表判符号",
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
            "analysis": _valid_analysis(),
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


def test_patch_analysis_must_match_schema(client) -> None:
    """BE-005 review 第 4 条：analysis 允许编辑写回，但形状必须还是 AnalysisResult。"""
    token = register_user(client)["access_token"]
    qid = _create(client, token, _choice_payload())["question"]["id"]

    bad = client.patch(
        f"/api/v1/questions/{qid}",
        json={"analysis": {"topic_type": "极值", "difficulty": "很难"}},
        headers=auth_headers(token),
    )
    assert bad.status_code == 400
    assert bad.json()["detail"]["code"] == "VALIDATION_ERROR"

    good = client.patch(
        f"/api/v1/questions/{qid}",
        json={
            "analysis": _valid_analysis(error_reasons=["没判符号变化"])
        },
        headers=auth_headers(token),
    )
    assert good.status_code == 200, good.text
    assert good.json()["analysis"]["topic_type"] == "导数与极值"

    # 清空分析仍然允许（analysis=null 不是坏结构）
    cleared = client.patch(
        f"/api/v1/questions/{qid}", json={"analysis": None}, headers=auth_headers(token)
    )
    assert cleared.status_code == 200
    assert cleared.json()["analysis"] is None


def test_create_keeps_image_path_for_intake_questions(client, db) -> None:
    """05 §6.4 的 `image_path?` 必须真落库。

    图片错题靠这一列关联原图，05 §5.2 还写明"多题共用同一 image_path，MVP 用它分组"。
    之前 schema 收了、service 建对象时没列这一行，于是题建得出来、原图关联静默丢失，
    列一直是 NULL——事后回补只能扫 uploads 目录猜，而文件名是内容寻址的，认不出归属。
    """
    from app.models.question import Question

    token = register_user(client)["access_token"]
    path = "uploads/1/6f1c2a3b4d5e6f70.jpg"

    first = _create(client, token, _choice_payload(source_type="image", image_path=path))["question"]
    second = _create(client, token, _blank_payload(source_type="image", image_path=path))["question"]
    assert first["image_path"] == path and second["image_path"] == path, "同一次提取的多题共用同一 image_path"

    detail = client.get(f"/api/v1/questions/{first['id']}", headers=auth_headers(token)).json()
    assert detail["image_path"] == path, "详情页要能据此取原图"

    text_only = _create(client, token, _choice_payload())["question"]
    assert text_only["image_path"] is None, "不带就是 null，不能把上一条的值串过来"

    # 错题本列表要显示原图，靠的是列表项这一项——逐条再请求一次详情不算实现
    page = client.get("/api/v1/questions", params={"page_size": 50}, headers=auth_headers(token)).json()
    listed = {x["id"]: x for x in page["items"]}
    assert listed[first["id"]]["image_path"] == path
    assert listed[second["id"]]["image_path"] == path
    assert listed[text_only["id"]]["image_path"] is None

    with db() as session:
        assert session.get(Question, first["id"]).image_path == path


def _patch(client, token: str, qid: int, body: dict):
    return client.patch(f"/api/v1/questions/{qid}", json=body, headers=auth_headers(token))


def test_patch_changes_question_type_and_clears_inapplicable_structure(client) -> None:
    """BE-025（issue #43）：题型结构三字段进可改清单，切换题型要清掉不适用的一半。

    前端 FE-027 已经能编辑选项/空位并 PATCH 上来；后端不收等于用户改的结构静默丢失，
    只能靠前端事后比对再提示"后端尚未支持"——那是把后端的活推给调用方兜。
    """
    token = register_user(client)["access_token"]
    q = _create(client, token, _choice_payload())["question"]
    assert q["question_type"] == "choice" and len(q["options"]) == 2

    blank = _patch(client, token, q["id"], {
        "question_type": "blank",
        "content_md": "$f(x)=x^2$ 的导数是 ___，极小值点是 ___。",
        "blanks": [{"index": 1, "answer_md": "$2x$"}, {"index": 2, "answer_md": "$0$"}],
    }).json()
    assert blank["question_type"] == "blank"
    assert blank["options"] is None, "切到填空题必须把选项清干净"
    assert len(blank["blanks"]) == 2

    solved = _patch(client, token, q["id"], {
        "question_type": "solve", "content_md": r"证明对任意实数 $x$，$x^2 \ge 0$。"
    }).json()
    assert solved["question_type"] == "solve"
    assert solved["options"] is None and solved["blanks"] is None

    bad = _patch(client, token, q["id"], {
        "question_type": "choice", "content_md": "下面哪个是对的？（  ）",
        "options": [{"label": "A", "content_md": "$1$"}],
    })
    assert bad.status_code == 400, bad.text
    assert client.get(f"/api/v1/questions/{q['id']}", headers=auth_headers(token)).json()["question_type"] == "solve", \
        "非法结构必须整笔回滚，不能把题型改一半"

    good = _patch(client, token, q["id"], {
        "question_type": "choice", "content_md": "下面哪个是对的？（  ）",
        "options": [{"label": "A", "content_md": "$1$"}, {"label": "B", "content_md": "$2$"}],
    })
    assert good.status_code == 200, good.text
    assert [o["label"] for o in good.json()["options"]] == ["A", "B"]


def test_patch_content_only_keeps_structure_intact(client) -> None:
    """只改题干不动结构：选项/空位保持原值，但题型规则仍要复核一遍。"""
    token = register_user(client)["access_token"]
    q = _create(client, token, _choice_payload())["question"]
    before = q["options"]

    after = _patch(client, token, q["id"], {"content_md": "求 $f(x)=x^3-3x$ 的极值。"}).json()
    assert after["options"] == before and after["question_type"] == "choice"


def test_patch_structure_error_message_is_readable(client) -> None:
    """400 的文案要中文可读：Pydantic 的默认英文串不该透到前端提示里（与识图同一口径）。"""
    token = register_user(client)["access_token"]
    q = _create(client, token, _blank_payload())["question"]

    resp = _patch(client, token, q["id"], {
        "content_md": "三个空：___、___ 和 ___。",
        "blanks": [{"index": 1, "answer_md": "$1$"}],
    })
    assert resp.status_code == 400, resp.text
    message = resp.json()["detail"]["message"]
    assert "Value error" not in message and "should have" not in message, message
