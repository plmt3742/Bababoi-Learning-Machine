# backend

Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic。

> 状态（2026-11-28）：核心闭环、统计（BE-013）、草稿（BE-018）、BYOK（BE-020）、
> 两步识图（BE-024）、图片录入（BE-014）均已实现；`uv run pytest` 全绿；
> OpenAPI 快照由 `scripts/export_openapi.py --check` 在 CI 校验。
> 待实现：`GET /practice/due` 今日待复习队列（#126）；MySQL 实跑迁移仍属 BE-011/OPS 收尾。
> 接口契约见 `docs/agent/05-architecture.md` 第 5/6 节。
>
> 出题质量的判据可以本地复现（要真 Key，脚本不打印密钥）：
> `uv run python scripts/measure_segment_similarity.py`

## 计划结构

```text
backend/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/       # 迁移脚本
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
├── fixtures/           # 合成题目/测试数据
├── data/               # SQLite（gitignore）
└── uploads/            # 上传文件（gitignore）
```

## 约定

- 数据库只用 SQLAlchemy ORM；不写方言 SQL。
- AI 输出必须经 Pydantic 校验才入库。
- LLM 调用不在数据库事务内；先调模型，再落库。
- 密钥只在 `.env`；提交 `.env.example`。
- 测试不调真实 LLM；用 mock/fixture。
- 共享工具放 `app/core/`；业务规则放 `app/services/`；AI 相关放 `app/ai/`。
- `fixtures/` 只放合成数据，不放真实学生题目/图片。
- 演示数据：`DEMO_PASSWORD='口令' uv run python scripts/seed_demo.py` 灌 `student01` / `student02`
  两个演示账号（两个账号是为了能验用户隔离和越权 403；口令由环境变量注入，不写进仓库）。
  脚本不调真实 LLM，重复执行不会重复插数据；改口令或题目答案后用 `--reset` 重建老库。

## 完成后命令

```bash
uv sync
uv run alembic upgrade head
DEMO_PASSWORD='<演示口令>' uv run python scripts/seed_demo.py   # 灌演示数据（可重复执行；口令必填）
# 管理端管理员（ADM-002；口令只从 shell 环境变量读，无默认值）
ADMIN_USERNAME=admin ADMIN_PASSWORD='<强口令>' ADMIN_EMAIL=admin@example.com uv run python scripts/seed_admin.py
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run python scripts/export_openapi.py   # 改 schema 后更新 contracts/openapi/openapi.json
```
