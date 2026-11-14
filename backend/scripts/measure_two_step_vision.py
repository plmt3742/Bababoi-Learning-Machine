"""BE-024 两跳识图的真模型复核（要 Key，不进 CI）。

    cd backend
    uv run python scripts/measure_two_step_vision.py [图片目录] [--runs 2]

默认目录 `D:/tmp-bababoi/real4`，默认每张跑 2 次。判定口径按 21 号 §2.6：
**四张图各 2 次，末题至少 1 次返回 + 带 incomplete/ warnings 的残缺可见**——
识图是概率行为，不比"每次都 5 条"。

输出：每张图每次的耗时、token、条数、题型分布、末题片段；结尾给汇总，并把
原始结果写 `D:/tmp-bababoi/be024-measure.json`。
"""
from __future__ import annotations

import base64
import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image  # noqa: E402

from app.ai import prompts, validator  # noqa: E402
from app.ai.client import OPERATION_VISION, DeepSeekClient  # noqa: E402
from app.ai.pipeline import run as pipeline_run  # noqa: E402
from app.core.config import settings  # noqa: E402

DEFAULT_DIR = Path("D:/tmp-bababoi/real4")
OUTPUT = Path("D:/tmp-bababoi/be024-measure.json")
MAX_EDGE = 1200

STEP1 = {
    "version": prompts.PROMPT_VERSION_VISION_TEXT,
    "max_tokens": 24000,
    "thinking": "adaptive",
}
STEP2 = {
    "version": prompts.PROMPT_VERSION_VISION_STRUCTURE,
    "max_tokens": 8000,
    "thinking": "disabled",
}


def _data_url(path: Path) -> str:
    image = Image.open(path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    if max(image.width, image.height) > MAX_EDGE:
        scale = MAX_EDGE / max(image.width, image.height)
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _one(image: Path, run: int, client: DeepSeekClient) -> dict:
    started = datetime.now()
    record: dict = {"image": image.name, "run": run, "ok": False}
    try:
        t1 = pipeline_run(
            client,
            OPERATION_VISION,
            prompts.vision_text_messages(_data_url(image)),
            custom_validate=validator.validate_transcript,
            retry_limit=1,
            max_tokens=STEP1["max_tokens"],
            thinking=STEP1["thinking"],
        )
        record.update(
            step1_ms=t1.usage.latency_ms,
            step1_out_tokens=t1.usage.completion_tokens,
            step1_attempts=t1.attempts,
        )
        transcript = t1.value
        record.update(chapter=transcript["chapter"], step1_count=len(transcript["questions"]))
        if not transcript["questions"]:
            record.update(ok=True, count=0, types={}, incomplete=0, last="", step2_ms=0)
            return record

        t2 = pipeline_run(
            client,
            OPERATION_VISION,
            prompts.vision_structure_messages(transcript),
            custom_validate=lambda raw: validator.validate_extraction(
                validator.normalize_blank_markers(raw)
            ),
            retry_limit=1,
            max_tokens=STEP2["max_tokens"],
            thinking=STEP2["thinking"],
        )
        questions = t2.value["questions"]
        for item in questions:
            item.chapter = transcript["chapter"]
        record.update(
            step2_ms=t2.usage.latency_ms,
            step2_out_tokens=t2.usage.completion_tokens,
            step2_attempts=t2.attempts,
            ok=True,
            count=len(questions),
            types={t: sum(1 for q in questions if q.question_type == t)
                   for t in ("choice", "blank", "solve")},
            incomplete=sum(1 for q in questions if q.incomplete),
            last=(questions[-1].content_md[:36] if questions else ""),
        )
    except Exception as exc:  # noqa: BLE001  一次失败不该中断整张矩阵
        record.update(ok=False, error=f"{type(exc).__name__}: {exc}")
    record["total_ms"] = int((datetime.now() - started).total_seconds() * 1000)
    return record


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    runs = 2
    for a in sys.argv[1:]:
        if a.startswith("--runs="):
            runs = int(a.split("=", 1)[1])
    folder = Path(args[0]) if args else DEFAULT_DIR
    images = sorted(p for p in folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
    if not images:
        raise SystemExit(f"{folder} 下没有 jpg/png")
    if not settings.llm_api_key:
        raise SystemExit("LLM_API_KEY 未配置——这个脚本只跑真模型")
    if settings.llm_mock:
        print("[warn] 本机 LLM_MOCK=true；脚本直接用 DeepSeekClient，不经 mock")

    client = DeepSeekClient()
    results = [_one(image, run, client) for image in images for run in range(1, runs + 1)]

    for row in results:
        head = f"{row['image']} #{row['run']}"
        if not row["ok"]:
            print(f"{head} FAIL {row['error']}")
            continue
        print(
            f"{head} count={row['count']} chapter={row['chapter']!r} "
            f"types={row['types']} incomplete={row['incomplete']} "
            f"step1={row['step1_ms']}ms/{row['step1_out_tokens']}tok "
            f"step2={row['step2_ms']}ms/{row['step2_out_tokens']}tok "
            f"total={row['total_ms']}ms"
        )
        print(f"    last: {row['last']}")

    print("\n[summary] 每张图：末题返回次数 / 条数 / 是否出现过 incomplete")
    for image in images:
        rows = [r for r in results if r["image"] == image.name]
        returned = sum(1 for r in rows if r.get("ok") and r.get("count", 0) > 0)
        counts = [r.get("count") for r in rows]
        incomplete = any(r.get("incomplete", 0) > 0 for r in rows)
        print(f"  {image.name}: 末题返回 {returned}/{len(rows)}，条数={counts}，incomplete={'有' if incomplete else '无'}")

    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n原始结果已写 {OUTPUT.as_posix()}")


if __name__ == "__main__":
    main()
