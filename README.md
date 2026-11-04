# Bababoi Learning Machine

把一道错题变成三道同类题，并追踪掌握度的 AI 错题巩固平台。

> 当前阶段：M0（产品设计 + 技术选型 + 仓库搭建）
> 目标用户：大学理科生（高数 / 线代 / 概率论 / 大学物理）
> 演示截止：11.29

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Arco Design Vue |
| 后端 | Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 |
| 数据库 | SQLite（本地/测试）+ MySQL 8（部署） |
| AI | DeepSeek `deepseek-flash`（文本 + 图像，OpenAI 兼容） |
| 部署 | Docker Compose + nginx；GitHub Actions（目标） |

## 仓库结构

```text
frontend/                 # Vue 3 前端（目录骨架，脚手架待 FE-001）
backend/                  # FastAPI 后端（目录骨架，脚手架待 BE-001）
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

## 本地启动

> 前后端脚手架尚未初始化（FE-001 / BE-001）。当前仓库只有目录与文档骨架。

```bash
# 前端（脚手架完成后）
cd frontend && pnpm install && pnpm dev

# 后端（脚手架完成后）
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

## 本地工具（不上传）

`tools/opencode-session-monitor/` 是本机的 OpenCode 会话/子 agent 监控面板，**只在本地使用，已加入 `.gitignore`，不上传仓库**。clone 后没有该目录是正常的；使用说明见本地文件。

## 注意

- `Resource/` 是本地只读参考资料，**不上传仓库**。
- 不提交 `.env`、API Key、数据库密码、`opencode.db`、上传文件。
- API 契约以 `docs/agent/05-architecture.md` 为准；改接口先改文档。
