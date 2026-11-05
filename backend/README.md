# backend

Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic，包管理用 uv。

> 状态：BE-001~003 已合进 `main`；BE-004~007、BE-012 在 PR #5/#6/#7/#9 上等 review。
> 契约以 `docs/agent/05-architecture.md` 为准（当前 v0.3.4），改接口先改那份文档。

## 跑起来

```bash
cd backend
uv sync
# Windows 直接双击 start-dev.bat；手工命令：
JWT_SECRET=至少32字节随机串 uv run alembic upgrade head
JWT_SECRET=... uv run uvicorn app.main:app --reload --port 8000
```

- API 文档：http://127.0.0.1:8000/docs
- 手工测试台：http://127.0.0.1:8000/static/test-console.html（本地/开发用，无鉴权，别上生产）
- 默认 `LLM_MOCK=true`，不需要 API Key 就能走通录题 → 分析 → 生成 → 练习全链路
- 换真模型：`.env` 里写 `LLM_API_KEY=...` + `LLM_MOCK=false`，再用
  `uv run python scripts/spike_llm.py`（加 `--analysis` / `--quiz`）单测连通性

## 检查

```bash
uv run ruff check app tests scripts
uv run pytest          # 全量 mock，不打真实 LLM、不起 worker 线程
```

## 目录

```text
backend/
├── app/
│   ├── main.py         # 只装配；lifespan 里按 task_workers_enabled 起停 worker
│   ├── core/           # config / security(JWT+bcrypt) / errors(统一信封) / observability
│   ├── db/             # engine / session / base（SQLite PRAGMA 见 §5.3）
│   ├── models/         # SQLAlchemy（9 张表，Alembic autogenerate 靠 __init__ 导出）
│   ├── schemas/        # Pydantic；题型规则的唯一来源在 schemas/question.py
│   ├── api/v1/         # 薄路由：health/auth/questions/tasks/practice/deps
│   ├── services/       # 业务规则与事务；task_worker 是队列消费端
│   ├── ai/             # client / prompts / parser / validator / pipeline（不碰 DB）
│   └── utils/
├── static/             # 手工测试台
├── scripts/            # spike_llm.py 等开发脚本
├── tests/              # pytest；conftest 用临时 SQLite + mock LLM
├── alembic/            # 迁移；initial schema = 7d155a41e345
└── start-dev.bat       # 一键起本地开发服务
```

## 约定

- 数据库只用 SQLAlchemy ORM，不写方言 SQL；SQLite 与 MySQL 共用一套 DDL（05 §5.3）。
- 题型规则只写一份：`schemas/question.py::validate_type_payload`，
  POST 校验、PATCH 复核、AI 输出校验都走它。
- AI 输出必须过 `app/ai/validator.py` 才入库；LLM 调用不在数据库事务内（05 §9.3）。
- 错误码只加不改，加完同步回写 05 §6.2 的表格。
- 密钥只在 `.env` / 服务器环境变量；仓库只提交 `.env.example`。
- 测试不调真实 LLM；worker 单测直接调同步函数，不起线程。
- `fixtures/` 只放合成数据，不放真实学生题目/图片。
