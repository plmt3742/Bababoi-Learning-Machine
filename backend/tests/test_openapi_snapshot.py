"""契约快照与运行时配置的一致性（BE-009 / 22 号 review #65）。"""
from __future__ import annotations

import json
from pathlib import Path

from app.core import meta
from app.core.config import Settings, settings

SNAPSHOT = Path(__file__).resolve().parents[2] / "contracts" / "openapi" / "openapi.json"


def test_snapshot_metadata_matches_runtime_config() -> None:
    """部署期用 .env 覆盖 VERSION/API_PREFIX 时，快照必须同步更新，否则这条会红。"""
    spec = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert spec["info"]["title"] == settings.project_name
    assert spec["info"]["version"] == settings.version
    assert all(path.startswith(settings.api_prefix) for path in spec["paths"])


def _iter_refs(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from _iter_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_refs(item)


def test_snapshot_refs_all_resolve() -> None:
    """合 openapi.json 时手解冲突可能丢 components、只留 path（#131/#132 review）。

    元数据测试抓不到；这里逐一解析所有 $ref，悬空引用直接红。
    """
    spec = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    refs = set(_iter_refs(spec))
    assert refs, "快照里没有任何 $ref，导出可能不完整"
    for ref in refs:
        assert ref.startswith("#/"), f"只支持本地引用：{ref}"
        node = spec
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            assert part in node, f"悬空 $ref：{ref}"
            node = node[part]


def test_config_defaults_come_from_meta_module() -> None:
    """默认值只有一份真源：导出脚本与 config 都从 app/core/meta.py 取。"""
    fields = Settings.model_fields
    assert fields["project_name"].default == meta.PROJECT_NAME
    assert fields["version"].default == meta.VERSION
    assert fields["api_prefix"].default == meta.API_PREFIX
