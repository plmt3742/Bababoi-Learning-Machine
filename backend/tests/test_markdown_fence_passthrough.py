"""#105：Markdown / Mermaid 围栏必须原样往返（后端不改写、不转义、不加转义符）。

前端渲染器按 ```mermaid 围栏识别图形；只要后端存回时动了一个字符，图的源码就会坏。
这条用真接口跑 create / PATCH / GET，逐字符比对。
"""
from __future__ import annotations

from tests.conftest import auth_headers, register_user

FLOW = "```mermaid\nflowchart LR\n  A[错题] --> B[AI 分析]\n  B --> C[生成相似题]\n```"
SEQUENCE = "```mermaid\nsequenceDiagram\n  Alice->>Bob: 交卷\n  Bob-->>Alice: 反馈\n```"

ANALYSIS = {
    "topic_type": "导数与极值",
    "difficulty": "medium",
    "knowledge_points": ["导数", "极值"],
    "error_reasons": ["未判断符号"],
    "answer_md": "极大值 $f(-1)=3$",
    "explanation_md": "求导后判符号。",
    "solution_summary": "先求导，再列表判符号：\n\n" + FLOW,
}


def test_fences_round_trip_through_create_patch_and_get(client) -> None:
    token = register_user(client)["access_token"]
    headers = auth_headers(token)
    payload = {
        "subject": "高等数学",
        "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。\n\n" + FLOW,
        "question_type": "solve",
        "answer_md": "答案：\n" + FLOW,
        "explanation_md": "解析：\n" + SEQUENCE,
    }

    created = client.post("/api/v1/questions", json=payload, headers=headers)
    assert created.status_code == 200, created.text
    question_id = created.json()["question"]["id"]

    detail = client.get(f"/api/v1/questions/{question_id}", headers=headers).json()
    assert detail["content_md"] == payload["content_md"]
    assert detail["answer_md"] == payload["answer_md"]
    assert detail["explanation_md"] == payload["explanation_md"]

    # PATCH 改回另一段围栏，读回仍逐字符一致
    patched_answer = "过程：\n" + SEQUENCE
    patched = client.patch(
        f"/api/v1/questions/{question_id}",
        json={"answer_md": patched_answer, "analysis": ANALYSIS},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    again = client.get(f"/api/v1/questions/{question_id}", headers=headers).json()
    assert again["answer_md"] == patched_answer
    assert again["analysis"]["solution_summary"] == ANALYSIS["solution_summary"]
