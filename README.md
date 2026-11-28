# Bababoi Learning Machine

把一道错题变成三道同类题，并追踪掌握度的 AI 错题巩固平台。

> 当前阶段：M1a 收尾（核心闭环已合，演示 11.29）
> 目标用户：大学理科生（高数 / 线代 / 概率论 / 大学物理）
> 演示截止：11.29

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Arco Design Vue |
| 后端 | Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 |
| 数据库 | SQLite（本地/测试）+ MySQL 8（部署） |
| AI | DeepSeek `deepseek-flash`（文本 + 图像，OpenAI 兼容） |
| 部署 | Docker Compose + nginx；GitHub Actions（目标） |

## 仓库结构

```text
frontend/                 # Vue 3 学生端（Calm Academic，页面已全部落地并完成真接口联调）
admin/                    # 内部运维台（ADR-005/009；进入 11.29 演示；后端地基 #123 已合，只读端点见 #124）
backend/                  # FastAPI 后端（认证 / 错题 / 三段生成 / 练习 / 统计 / 识图 / 草稿 / BYOK 已合）
contracts/                # 前后端共享契约（OpenAPI / 示例）
deploy/                   # Docker Compose / nginx / 部署说明
scripts/                  # 跨前后端的开发脚本
docs/
├── agent/                # agent 工程上下文（先读 00-context）
├── product/              # PRD / IA / 页面规范 / 设计系统 / UE 稿
└── adr/                  # 架构决策记录
.github/                  # CI / Issue / PR 模板
AGENTS.md                 # 任何 AI agent 的第一入口
Resource/                 # 本地只读参考资料（不上传仓库）
```

## 先读什么

- 第一次进入项目：`docs/agent/00-context.md`
- 当前任务：`docs/agent/04-todos.md`
- API / 数据模型：`docs/agent/05-architecture.md`
- 协作流程：`docs/agent/07-workflow.md`
- 设计手册：`docs/agent/08-design-playbook.md`
- 风险：`docs/agent/09-risks.md`

## 当前进度（2026-11-28）

- `origin/main`（截至 2026-11-28）：后端核心闭环已合（认证与多设备会话、错题 CRUD、分析、三段并发生题、排队取消、识图任务化、练习、统计、草稿、BYOK、限流、改密登出）；管理端地基 #123 已合（角色/禁用/审计/管理员登录）
- 前端：学生端页面全部落地，真接口联调完成（练习 / 图片 / 草稿 / 统计 / 偏好）
- 收尾：ADR-010 密码重置（线上申请 + 管理员审批）文档定稿；#114 越权软删、#115 搜索大小写两个边界问题已修（本 PR）
- 管理端：ADR-005 + ADR-009；`admin/` 进入 11.29 演示（范围见 `docs/agent/28-admin-console.md`）；只读端点见 #124
- 图片录入 v2（正式决策）：用户裁剪 → 多题文本提取（①②…）→ 逐条确认 → 分析/答案/解析 → 选择 1–3 道生成；不做 bbox/框题
- 范围 / 交互 / 验收以 `docs/product/01-prd-lite.md` + `02-ia-and-flows.md` + `03-page-specs.md` 为准

## 本地启动

> 前后端都能本地起；后端需要 `uv` 与 `JWT_SECRET`（≥32 字节），默认 `LLM_MOCK=true` 不调真实模型。

```bash
# 前端
cd frontend && pnpm install && pnpm dev

# 后端
cd backend && uv sync
cp .env.example .env                                            # 填 JWT_SECRET（≥32 字节）
uv run alembic upgrade head
uv run uvicorn app.main:app --reload                            # http://127.0.0.1:8000/api/v1/health
uv run ruff check app tests && uv run pytest                    # 检查与测试
# 可选：灌演示数据（APP_ENV / DEMO_PASSWORD 走进程环境变量，见 .env.example）
uv run python scripts/seed_demo.py
```

## 本地工具（不上传）

`tools/opencode-session-monitor/` 是本机的 OpenCode 会话/子 agent 监控面板，**只在本地使用，已加入 `.gitignore`，不上传仓库**。clone 后没有该目录是正常的；使用说明见本地文件。

## 注意

- `Resource/` 是本地只读参考资料，**不上传仓库**。
- 不提交 `.env`、API Key、数据库密码、`opencode.db`、上传文件。
- API 契约以 `docs/agent/05-architecture.md` 为准；改接口先改文档。
