"""真模型 spike：人工验证 DeepSeek 连通性与输出质量（不进 CI）。

用法：
    cd backend
    # .env 里配好 LLM_API_KEY、LLM_MOCK=false
    uv run python scripts/spike_llm.py            # 跑分析 + 生成
    uv run python scripts/spike_llm.py --analysis # 只跑分析
    uv run python scripts/spike_llm.py --quiz     # 只跑生成

输出会打印原始回复与校验结果；报错时按 12号 §6.2 把现象记进对接文档。
"""
from __future__ import annotations

import argparse
import json
import sys

# Windows 控制台默认 GBK，中文 JSON 会显示成乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.ai import prompts, validator  # noqa: E402
from app.ai.client import OPERATION_ANALYSIS, OPERATION_QUIZ, build_llm_client  # noqa: E402
from app.ai.pipeline import run  # noqa: E402

SAMPLE_QUESTION = {
    "subject": "高等数学",
    "question_type": "solve",
    "content_md": "求函数 $f(x)=x^3-3x+1$ 的极值。",
    "answer_md": "极大值 $f(-1)=3$，极小值 $f(1)=-1$",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", action="store_true")
    ap.add_argument("--quiz", action="store_true")
    args = ap.parse_args()
    do_all = not args.analysis and not args.quiz

    client = build_llm_client()
    print(f"client={type(client).__name__} model={getattr(client, '_model', 'mock')}")

    if do_all or args.analysis:
        print("\n=== 分析 ===")
        result = run(client, OPERATION_ANALYSIS, prompts.analysis_messages(SAMPLE_QUESTION),
                     parse=validator.AnalysisResult)
        print("原始回复：", result.usage.text[:500])
        print(f"[attempts={result.attempts} tokens={result.usage.prompt_tokens}+"
              f"{result.usage.completion_tokens} {result.usage.latency_ms}ms]")
        print("校验通过：", result.value.model_dump_json(indent=2, ensure_ascii=False))

    if do_all or args.quiz:
        print("\n=== 生成 3 题 ===")
        result = run(client, OPERATION_QUIZ, prompts.quiz_messages(SAMPLE_QUESTION),
                     custom_validate=validator.validate_quiz)
        print("原始回复：", result.usage.text[:800])
        print(f"[attempts={result.attempts} tokens={result.usage.prompt_tokens}+"
              f"{result.usage.completion_tokens} {result.usage.latency_ms}ms]")
        for index, spec in enumerate(result.value, start=1):
            print(f"--- 第 {index} 题 [{spec.question_type}/{spec.difficulty}] ---")
            print(json.dumps(spec.model_dump(), ensure_ascii=False, indent=2)[:600])


if __name__ == "__main__":
    main()
