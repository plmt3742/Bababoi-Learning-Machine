# Bababoi Learning Machine

把一道错题变成三道同类题，并追踪掌握度的 AI 错题巩固平台。

> 当前阶段：M0 收尾 / 11.29 演示准备（2026-11-28）
> 目标用户：大学理科生（高数 / 线代 / 概率论 / 大学物理）
> 演示截止：11.29

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Arco Design Vue + Markdown/KaTeX/Mermaid |
| 后端 | Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 |
| 数据库 | SQLite（本地/测试）+ MySQL 8（部署） |
| AI | DeepSeek `deepseek-flash`（文本 + 图像，OpenAI 兼容） |
| 部署 | Docker Compose + nginx；GitHub Actions（目标） |

## 仓库结构

```text
frontend/                 # Vue 3 学生端（Calm Academic，FE-001~037 页面已完成）
admin/                    # 内部运维台（ADR-005/009；进入 11.29 演示）
backend/                  # FastAPI 后端（核心闭环 + 统计/草稿/BYOK/识图已实现）
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

- 前端：FE-001~037 页面与核心联调完成；错题录入/列表/详情、练习、统计、任务中心、设置、图片录入、草稿、生成偏好均可用；Mermaid 解析/答案按需渲染已接入（ADR-011）。
- 后端：认证、错题 CRUD、AI 分析、三段并发生成、任务队列、练习记录、统计、草稿、BYOK、两步识图、图片录入已实现；`GET /practice/due` 契约已定，待实现（#126）。
- 管理端：ADR-005 + ADR-009；`admin/` 进入 11.29 演示（范围见 `docs/agent/28-admin-console.md`）。
- 演示前待收口：后端 #114（越权软删）/ #115（搜索大小写）修复；`GET /practice/due` 后端 #126；打印卷与今日待复习前端已完成、待 PR；staging 已于 11-17 更新并回归（见 24 号文档）。
- 范围 / 交互 / 验收以 `docs/product/01-prd-lite.md` + `02-ia-and-flows.md` + `03-page-specs.md` 为准。

## 本地启动

> 前后端均可运行；前端默认 mock，联调时把 `frontend/.env.local` 的 `VITE_USE_MOCK` 设为 `false`。

```bash
# 前端
cd frontend && pnpm install && pnpm dev

# 后端（需要 uv 和 JWT_SECRET）
cd backend && uv sync && uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000/api/v1/health
cd backend && uv run ruff check app tests && uv run pytest      # 检查与测试
```

## 本地工具（不上传）

`tools/opencode-session-monitor/` 是本机的 OpenCode 会话/子 agent 监控面板，**只在本地使用，已加入 `.gitignore`，不上传仓库**。clone 后没有该目录是正常的；使用说明见本地文件。

## 注意

- `Resource/` 是本地只读参考资料，**不上传仓库**。
- 不提交 `.env`、API Key、数据库密码、`opencode.db`、上传文件。
- API 契约以 `docs/agent/05-architecture.md` 为准；改接口先改文档。
