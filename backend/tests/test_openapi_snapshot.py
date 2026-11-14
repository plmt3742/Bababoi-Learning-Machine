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


def test_config_defaults_come_from_meta_module() -> None:
    """默认值只有一份真源：导出脚本与 config 都从 app/core/meta.py 取。"""
    fields = Settings.model_fields
    assert fields["project_name"].default == meta.PROJECT_NAME
    assert fields["version"].default == meta.VERSION
    assert fields["api_prefix"].default == meta.API_PREFIX
