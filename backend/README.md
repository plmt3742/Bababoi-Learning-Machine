# backend

Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic。

> 状态（2026-11-06）：核心闭环已实现——认证、错题 CRUD、AI 分析、生成（ADR-006 三段并发）、
> 任务队列、练习记录；`uv run pytest` 全绿。
> 仍待实现：草稿（BE-018）、统计（BE-013）、BYOK（BE-020）。图片上传与多题文本提取（BE-014）在 PR #40。
> 数据库 schema 最终由人机负责；接口契约见 `docs/agent/05-architecture.md` 第 5/6 节，
> 对接进度与待拍板项见 `docs/agent/15-backend-sync-20261106.md`。
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
uv run python scripts/seed_demo.py   # 灌演示数据（可重复执行）
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
```
