# Bababoi Learning Machine

把一道错题变成三道同类题，并追踪掌握度的 AI 错题巩固平台。

> 当前阶段：M2（功能完整 + staging 真机走查；11.22 功能冻结）
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
frontend/                 # Vue 3 学生端（Calm Academic，FE-001~035 已完成）
admin/                    # P1 内部运维台（占位，ADR-005；不进入 11.29 演示）
backend/                  # FastAPI 后端（核心闭环 + 草稿/统计/识图/偏好/OpenAPI 已合）
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

## 当前进度（2026-11-15）

- `origin/main @ 7ab9cf9`：认证/错题/分析/生成/任务/练习/图片识图/草稿/统计/生成偏好/OpenAPI 快照/识图两步与缓存已合；前端 FE-001~035 已合
- 后端：pytest 223 passed；#67 两步识图、#71 识图缓存、#58/#62/#63/#64/#65 已合；待处理 BE-020 BYOK、BE-011 MySQL、BE-016 必需加固、OPS
- 前端：FE-001~035 页面完成，Vitest 9 files / 35 tests，`frontend/dist/` 可构建；没有新的 P0 功能任务，下一步是 staging 真机走查、生产模式/100+ 数据回归与 SH-014 录屏/截图
- **staging：截至 2026-11-15 仍无 URL**；11.14 已过，R-009 已触发；`deploy/` 只有 README
- 管理端：ADR-005 已定 `admin/` 为 P1 内部运维台，不进入 11.29 演示；当前仅占位
- 图片录入 v2（正式决策）：用户裁剪 → 多题文本提取（①②…）→ 逐条确认 → 分析/答案/解析 → 选择 1–3 道生成；不做 bbox/框题
- 范围 / 交互 / 验收以 `docs/product/01-prd-lite.md` + `02-ia-and-flows.md` + `03-page-specs.md` 为准

## 本地启动

> 前后端均可本地运行；前端开发模式默认 mock，切真实后端用 `VITE_USE_MOCK=false`。

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
