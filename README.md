# Bababoi Learning Machine

把一道错题变成三道同类题，并追踪掌握度的 AI 错题巩固平台。

> 当前阶段：11.29 演示收尾（学生端闭环 + 管理端基础 + 部署/PPT）
> 目标用户：大学理科生（高数 / 线代 / 概率论 / 大学物理）
> 演示截止：11.29 15:00

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
frontend/                 # Vue 3 学生端（Calm Academic，FE-001~039）
admin/                    # 内部运维台（占位，ADR-005/009；进入 11.29 演示）
backend/                  # FastAPI 后端（认证/错题/分析/生成/任务/练习/识图/草稿/统计已合）
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

- `origin/main`：学生端闭环（认证/错题/分析/生成/任务/练习/图片识图/草稿/统计/生成偏好/OpenAPI）已合；FE-001~039 页面与测试、联调收口已合；管理端文档（ADR-009/010）与管理端后端地基（#123）已合
- 后端待处理：BE-015 单题重生成/质量反馈、BE-016 性能/安全加固、OPS/部署收尾；管理端后端地基 #123 已合，admin 前端 PR #120 待合，ADM-003+ 待做
- 前端：FE-001~039 已合；FE-040 忘记密码/强制改密待 BE-030；管理端前端 PR #120 待合
- 管理端：ADR-005 + ADR-009；`admin/` 进入 11.29 演示（范围见 `docs/agent/28-admin-console.md`）；主分支 `admin/` 仍为占位，后端地基 #123 已合，前端见 PR #120
- 图片录入 v2（正式决策）：用户裁剪 → 多题文本提取（①②…）→ 逐条确认 → 分析/答案/解析 → 选择 1–3 道生成；不做 bbox/框题
- 范围 / 交互 / 验收以 `docs/product/01-prd-lite.md` + `02-ia-and-flows.md` + `03-page-specs.md` 为准

## 本地启动

> 前后端均可运行；前端 `pnpm dev` 默认 mock，后端需要 `.env`（JWT_SECRET、LLM_MOCK=true）。

```bash
# 前端
cd frontend && pnpm install && pnpm dev

# 后端（已可用；需要 uv 和 JWT_SECRET）
cd backend && uv sync && uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000/api/v1/health
cd backend && uv run ruff check app tests && uv run pytest      # 检查与测试
```

## 本地工具（不上传）

`tools/opencode-session-monitor/` 是本机的 OpenCode 会话/子 agent 监控面板，**只在本地使用，已加入 `.gitignore`，不上传仓库**。clone 后没有该目录是正常的；使用说明见本地文件。

## 注意

- `Resource/` 是本地只读参考资料，**不上传仓库**。
- 不提交 `.env`、API Key、数据库密码、`opencode.db`、上传文件。
- API 契约以 `docs/agent/05-architecture.md` 为准；改接口先改文档。
