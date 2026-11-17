"""共享 fixture：临时 SQLite + TestClient（JWT 注入）+ 注册/鉴权辅助。

每个测试拿到的是独立库（tmp_path）和干净的限流器，互不影响。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.services.auth_service import login_limiter

TEST_SECRET = "unit-test-secret-0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _force_mock_llm(monkeypatch):
    """整个测试套件强制 LLM_MOCK=true。

    CI 环境本来就是这样，但开发机上的 backend/.env 常常是 false——
    依赖环境默认值的测试会在某台机器上真的去打 DeepSeek，既慢又烧钱，还可能改坏数据。
    需要假客户端的用例自己 monkeypatch 替身，需要看"未配置"分支的用例自己再改回去。
    """
    monkeypatch.setattr(settings, "llm_mock", True)


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(db, tmp_path, monkeypatch):
    def override_session():
        s = db()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(settings, "jwt_secret", TEST_SECRET)
    monkeypatch.setattr(settings, "task_workers_enabled", False)  # worker 单测自己调同步函数
    # 上传的图落到临时目录：不隔离的话测试会往仓库 backend/uploads/ 里写真文件
    monkeypatch.setattr(settings, "upload_dir", (tmp_path / "uploads").as_posix())
    login_limiter.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_user(
    client: TestClient, username: str = "小明_01", password: str = "p@ssw0rd9"
) -> dict:
    resp = client.post(
        "/api/v1/auth/register", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
