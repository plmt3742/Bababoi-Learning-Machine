# backend

Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic。

> 状态：目录骨架。脚手架任务 `BE-001`，见 `docs/agent/04-todos.md`。
> 数据库 schema 最终由周彧良负责；`docs/agent/05-architecture.md` 第 5 节是草案。

## 计划结构

```text
backend/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── alembic.ini
├── alembic/
├── app/
│   ├── main.py
│   ├── core/           # config / security / logging / errors
│   ├── db/             # engine / session / base
│   ├── models/         # SQLAlchemy
│   ├── schemas/        # Pydantic
│   ├── api/v1/         # routers
│   ├── services/       # business logic
│   ├── ai/             # client / prompts / parser / validator / vision
│   └── utils/
├── tests/
├── scripts/            # seed / dev
├── data/               # SQLite（gitignore）
└── uploads/            # 上传文件（gitignore）
```

## 约定

- 数据库只用 SQLAlchemy ORM；不写方言 SQL。
- AI 输出必须经 Pydantic 校验才入库。
- LLM 调用不在数据库事务内；先调模型，再落库。
- 密钥只在 `.env`；提交 `.env.example`。
- 测试不调真实 LLM；用 mock/fixture。

## 完成后命令

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
```
