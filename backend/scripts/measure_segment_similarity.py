"""复现「与原题相似度 0.9 阈值没有鉴别力」的那组实测数据（ADR-006 / 05 §7.2 第 3 条）。

为什么要留这个脚本：三段并发把生题从"一次 3 道"改成"一次 1 道"之后，
单段的题干更容易贴着原题写（只换函数式），原来 batch 时代定的 `相似度 <0.9` 判据
开始成批把合法输出判死。这个数字结论得能被别人重跑，不然只是一句转述。

用法（要 backend/.env 里有真 Key，且 LLM_MOCK=false；脚本不打印 Key）：

    cd backend && uv run python scripts/measure_segment_similarity.py
    cd backend && uv run python scripts/measure_segment_similarity.py "求函数 $f(x)=x^3-3x$ 的极值。"

看最后那段汇总：`≥0.9 的段数` 与 `逐字抄题的段数` 是分开的两件事——
前者一堆、后者零，才是"阈值该改成逐字相同"的依据。
"""
from __future__ import annotations

import json
import statistics
import sys
import time

from app.ai import prompts, validator
from app.ai.client import OPERATION_QUIZ, build_llm_client
from app.core.config import settings

ROUNDS = 3
DEFAULT_ORIGINAL = "设函数 $f(x)=x-a\\ln x$（$a\\in\\mathbb{R}$），讨论 $f(x)$ 的单调性。"
DIFFICULTIES = ("easy", "medium", "hard")


def main() -> None:
    original = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ORIGINAL
    question = {
        "subject": "高等数学",
        "question_type": "solve",
        "content_md": original,
        "knowledge_points": ["导数与单调性", "含参讨论", "定义域"],
        "tags": ["含参", "导数"],
    }
    print(f"llm_mock={settings.llm_mock} model={settings.llm_model}\n原题={original}\n")
    client = build_llm_client()

    sims: list[float] = []
    out_tokens: list[int] = []
    verbatim = 0
    bad_shape = 0
    for round_no in range(1, ROUNDS + 1):
        for slot, difficulty in enumerate(DIFFICULTIES, start=1):
            messages = prompts.quiz_messages(question, target_index=slot, difficulty=difficulty)
            started = time.perf_counter()
            resp = client.complete(OPERATION_QUIZ, messages)
            wall = time.perf_counter() - started
            raw = json.loads(resp.text)
            content = raw.get("content_md") or ""
            sim = validator.similarity(content, original)
            normalized_same = (
                validator._normalize_for_compare(content)
                == validator._normalize_for_compare(original)
            )
            sims.append(sim)
            out_tokens.append(resp.completion_tokens)
            verbatim += normalized_same
            try:
                validator.validate_segment(raw, difficulty=difficulty, original_content_md=original)
                verdict = "通过"
            except ValueError as exc:
                bad_shape += "validation errors" in str(exc)
                verdict = f"判死：{str(exc)[:60]}"
            print(f"[R{round_no} 段{slot} {difficulty}] {wall:.1f}s out={resp.completion_tokens} "
                  f"type={raw.get('question_type')} 自标={raw.get('difficulty')} "
                  f"相似度={sim:.3f} 逐字相同={normalized_same} {verdict}")
            print("   ", content.replace("\n", " ")[:130])

    print("\n== 汇总 ==")
    print(f"样本={len(sims)} 相似度 最小={min(sims):.3f} 中位={statistics.median(sims):.3f} "
          f"最大={max(sims):.3f} ≥0.9 段数={sum(1 for s in sims if s >= 0.9)}")
    print(f"真正逐字抄原题的段数={verbatim}（这才是要拦的）")
    print(f"形状就不合法的段数={bad_shape}（模型吐了非题目 JSON，重试一次通常就好）")
    print(f"单段输出 token：最大={max(out_tokens)}（对着 SAMPLING[quiz]['max_tokens'] 看余量）")


if __name__ == "__main__":
    main()
