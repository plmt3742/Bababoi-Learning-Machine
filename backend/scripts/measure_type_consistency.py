"""量 strict 模式（generate_v3）下「题型与原题一致」的真实失败率（BE-026 / 前端 review）。

为什么要这个脚本：`MockLLMClient` 的假卡是按「题型 × 难度」写死的，它只能证明链路
不会自己判死，证明不了真模型会照 strict 提示词出同题型题。这个脚本用真模型跑一遍，
给出可复现的数字（2026-11-10：27/27 题型一致、27/27 校验通过）。

用法（backend/.env 要有真 Key，且 LLM_MOCK=false；脚本不打印 Key）：

    cd backend && uv run python scripts/measure_type_consistency.py
    cd backend && uv run python scripts/measure_type_consistency.py --rounds 2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from app.ai import prompts, validator  # noqa: E402
from app.ai.client import OPERATION_QUIZ, build_llm_client
from app.core.config import settings

ROUNDS = 3
DIFFICULTIES = ("easy", "medium", "hard")

ORIGINALS = [
    {
        "subject": "高等数学",
        "question_type": "solve",
        "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
        "answer_md": "极大值 $f(-1)=3$，极小值 $f(1)=-1$",
        "knowledge_points": ["导数", "极值"],
        "tags": ["导数"],
    },
    {
        "subject": "高等数学",
        "question_type": "choice",
        "content_md": "设 $f(x)=x^2-2x+3$，则 $f(x)$ 的最小值为（ ）。",
        "answer_md": "选 B",
        "knowledge_points": ["二次函数", "配方法"],
        "tags": [],
    },
    {
        "subject": "高等数学",
        "question_type": "blank",
        "content_md": "计算极限 $\\lim_{x\\to 0}\\dfrac{\\sin 3x}{x}= $ ___。",
        "answer_md": "$3$",
        "knowledge_points": ["极限", "等价无穷小"],
        "tags": [],
    },
]


def main() -> None:
    rounds = ROUNDS
    if len(sys.argv) == 3 and sys.argv[1] == "--rounds":
        rounds = int(sys.argv[2])
    print(f"llm_mock={settings.llm_mock} model={settings.llm_model} rounds={rounds}\n")
    if settings.llm_mock:
        raise SystemExit("LLM_MOCK=true：mock 的题型是写死的，量出来的失败率没有意义")
    client = build_llm_client()

    total = matched = passed = 0
    for original in ORIGINALS:
        expect = original["question_type"]
        for round_no in range(1, rounds + 1):
            for slot, difficulty in enumerate(DIFFICULTIES, start=1):
                messages = prompts.quiz_messages(
                    original, target_index=slot, difficulty=difficulty, type_policy="strict")
                resp = client.complete(OPERATION_QUIZ, messages)
                raw = json.loads(resp.text)
                actual = raw.get("question_type")
                total += 1
                same = actual == expect
                matched += same
                verdict = "通过"
                try:
                    validator.validate_segment(
                        raw, difficulty=difficulty,
                        original_content_md=original["content_md"],
                        original_question_type=expect, type_policy="strict",
                    )
                    passed += 1
                except ValueError as exc:
                    verdict = f"判死：{str(exc)[:70]}"
                print(f"[{expect} R{round_no} 段{slot} {difficulty}] "
                      f"type={actual} 一致={same} {verdict}")

    print("\n== 汇总 ==")
    print(f"调用={total} 题型一致={matched} ({matched / total:.0%}) "
          f"校验通过={passed} ({passed / total:.0%})")
    print("严格模式下每次任务最多跑 2 次（任务级 requeue 1 次），"
          "按一致率 r 粗算整段失败率≈(1-r)^2；这就是默认开启要多花的 LLM 调用。")


if __name__ == "__main__":
    main()
