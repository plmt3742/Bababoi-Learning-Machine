"""导出 OpenAPI 契约快照（BE-009 / 21号 §1-5）。

    cd backend
    uv run python scripts/export_openapi.py           # 写 contracts/openapi/openapi.json
    uv run python scripts/export_openapi.py --check   # 只比对不写（CI 用）

输出必须确定性：键排序 + 固定缩进 + 结尾换行 + LF 行尾，否则不同机器/字典序会让
CI 的 diff 检查误报。`--check` 与写文件共用同一个 `render()`，避免"检查的和提交的
不是同一份序列化"。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# 默认值从 app.core.meta 读（该模块不实例化 Settings，import 它不会读 .env）。
# 不能先 import app.core.config 再覆写 env：config.py 在 import 时就建好 settings 单例，
# 之后再改 os.environ 对已缓存的 settings 无效，.env 里的 VERSION/API_PREFIX 仍会漏进快照。
from app.core.meta import API_PREFIX as _DEFAULT_API_PREFIX  # noqa: E402
from app.core.meta import PROJECT_NAME as _DEFAULT_PROJECT_NAME  # noqa: E402
from app.core.meta import VERSION as _DEFAULT_VERSION  # noqa: E402

# 导出必须只取决于代码：PROJECT_NAME/VERSION/API_PREFIX 也会进快照，
# 本机 .env 若设了这些键（或环境里导出过），生成物就和 CI 不一致——这里直接覆盖。
os.environ["LLM_MOCK"] = "true"
os.environ["PROJECT_NAME"] = _DEFAULT_PROJECT_NAME
os.environ["VERSION"] = _DEFAULT_VERSION
os.environ["API_PREFIX"] = _DEFAULT_API_PREFIX

from app.main import app  # noqa: E402

OUTPUT = REPO_ROOT / "contracts" / "openapi" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    content = render()
    if "--check" in sys.argv[1:]:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(
                "OpenAPI 快照与代码不一致：先在 backend/ 跑 "
                "`uv run python scripts/export_openapi.py` 再提交",
                file=sys.stderr,
            )
            sys.exit(1)
        print("OpenAPI 快照一致")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"已写入 {OUTPUT.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
