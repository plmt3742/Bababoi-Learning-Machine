"""迁移可跑（BE-002 验收项）。

用 alembic 的 Python API 而不是 shell，CI 上才不需要额外配置。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "users",
    "questions",
    "tags",
    "question_tags",
    "generated_questions",
    "generation_task",
    "draft",
    "practice_records",
    "ai_call_logs",
    "vision_extract_cache",
}


def _config(db_path: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def test_upgrade_head_creates_every_table(tmp_path, monkeypatch) -> None:
    db = tmp_path / "migrated.db"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", f"sqlite:///{db.as_posix()}")

    cfg = _config(db)
    command.upgrade(cfg, "head")

    tables = {
        row[0]
        for row in sqlite3.connect(db).execute(
            "select name from sqlite_master where type='table'"
        )
    }
    assert EXPECTED_TABLES <= tables, f"缺表：{EXPECTED_TABLES - tables}"


def test_upgrade_from_published_cache_revision_adds_columns(tmp_path, monkeypatch) -> None:
    """`b7c2f4a91d30` 已发布过：跑过旧版的人必须能靠前向迁移补列，而不是重建库。"""
    db = tmp_path / "patched.db"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    cfg = _config(db)
    command.upgrade(cfg, "b7c2f4a91d30")
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db)
    columns = {row[1] for row in conn.execute("pragma table_info(vision_extract_cache)")}
    assert {"model", "last_forced_at"} <= columns

    table_sql = conn.execute(
        "select sql from sqlite_master where type='table' and name='vision_extract_cache'"
    ).fetchone()[0]
    normalized = " ".join(table_sql.split())
    assert "subject_key, model" in normalized, "唯一键必须扩成含 model"


def test_downgrade_merges_rows_that_differ_only_by_model(tmp_path, monkeypatch) -> None:
    """唯一键要缩回 5 列：同图两种 model 的两行会撞键，降级前必须先合并掉重复行。"""
    db = tmp_path / "downgrade.db"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    cfg = _config(db)
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db)
    for model in ("deepseek-flash", "deepseek-v4-pro"):
        conn.execute(
            "insert into vision_extract_cache"
            " (user_id, image_sha, subject_key, model, hop1_version, hop2_version,"
            "  payload, question_count, has_incomplete, hit_count, created_at)"
            " values (1, ?, '', ?, 'vision_text_v1', 'vision_structure_v1',"
            "  '{}', 0, 0, 0, '2026-11-12 00:00:00')",
            ("0" * 16, model),
        )
    conn.commit()
    conn.close()

    command.downgrade(cfg, "b7c2f4a91d30")

    conn = sqlite3.connect(db)
    assert conn.execute("select count(*) from vision_extract_cache").fetchone()[0] == 1
    columns = {row[1] for row in conn.execute("pragma table_info(vision_extract_cache)")}
    assert "model" not in columns
    conn.close()

    command.upgrade(cfg, "head")  # 降级后还能再升回来


def test_downgrade_to_base_empties_the_schema(tmp_path, monkeypatch) -> None:
    """迁移必须可逆，否则生产上出错就只能手工删表。"""
    db = tmp_path / "rolled.db"
    url = f"sqlite:///{db.as_posix()}"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", url)

    cfg = _config(db)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    tables = {
        row[0]
        for row in sqlite3.connect(db).execute(
            "select name from sqlite_master where type='table'"
        )
    }
    assert EXPECTED_TABLES & tables == set()


def test_metadata_and_migration_stay_in_sync(tmp_path, monkeypatch) -> None:
    """模型改了忘记生成迁移时，这条会红——比等到联调才发现好。"""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.db.base import Base
    from app.models import (  # noqa: F401  确保所有模型已注册
        AiCallLog,
        Draft,
        GeneratedQuestion,
        GenerationTask,
        PracticeRecord,
        Question,
        QuestionTag,
        Tag,
        User,
    )

    db = tmp_path / "drift.db"
    url = f"sqlite:///{db.as_posix()}"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", url)
    command.upgrade(_config(db), "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        diff = compare_metadata(context, Base.metadata)
    assert diff == [], f"模型与迁移不一致：{diff}"
