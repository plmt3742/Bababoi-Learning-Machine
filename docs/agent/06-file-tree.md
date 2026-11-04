---
owner: 霹雳马桶
last_updated: 2026-11-05
status: active
read_when: 新建文件/目录前；review 目录结构时；agent 不确定文件该放哪时
---

# 06 · 文件树与目录职责

## 1. 当前状态

```text
BababoiLearningMachine/
├── AGENTS.md
├── README.md                      # 项目说明/结构/快速开始
├── .gitignore                     # Resource/、.env、依赖、数据等不上传
├── Resource/
│   └── 基于生成式AI的错题整理系统.docx   # 本地只读参考，不上传仓库
├── frontend/
│   ├── README.md                  # 目录骨架；脚手架待 FE-001
│   ├── src/.gitkeep
│   └── tests/.gitkeep
├── backend/
│   ├── README.md                  # 目录骨架；脚手架待 BE-001
│   ├── app/.gitkeep
│   └── tests/.gitkeep
├── deploy/
│   └── README.md                  # compose/nginx 待补
├── tools/                         # 本地工具，不上传（gitignore）
│   ├── README.md
│   └── opencode-session-monitor/  # 本地会话/子 agent 监控
└── docs/
    ├── README.md
    ├── adr/
    │   ├── README.md
    │   ├── ADR-000-template.md
    │   ├── ADR-001-tech-stack.md
    │   ├── ADR-002-mvp-scope.md
    │   └── ADR-003-image-input-vision.md
    ├── agent/
    │   ├── README.md
    │   ├── 00-context.md
    │   ├── 01-project.md
    │   ├── 02-goals.md
    │   ├── 03-roadmap.md
    │   ├── 04-todos.md
    │   ├── 05-architecture.md
    │   ├── 06-file-tree.md
    │   ├── 07-workflow.md
    │   ├── 08-design-playbook.md
    │   ├── 09-risks.md
    │   ├── 10-resources.md
    │   └── 11-agent-handoff.md
    ├── learning/                    # 本地学习笔记（gitignore，不上传）
    └── product/
        ├── README.md
        ├── 01-prd-lite.md
        ├── 02-ia-and-flows.md
        ├── 03-page-specs.md
        └── 04-design-system.md
```

> `frontend/`、`backend/`、`deploy/` 目录骨架已建立；真正的脚手架（Vue/Vite、FastAPI、compose）待 `FE-001` / `BE-001` / `OPS-001`。下图是完整目标结构。

## 2. 目标文件树

```text
BababoiLearningMachine/
├── AGENTS.md                      # agent 第一入口
├── README.md                      # 给人看的项目说明 + 快速开始
├── .gitignore
├── .gitattributes                 # 统一换行符
├── .editorconfig
├── docs/
│   ├── README.md                  # 文档总索引
│   ├── agent/                     # agent 工程上下文（本目录）
│   ├── product/                   # 产品设计产出
│   └── adr/                       # 架构决策记录
├── frontend/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── .env.example
│   ├── public/                    # 静态资源
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── api/                   # HTTP 客户端、端点、类型
│   │   ├── assets/                # 图片/字体等静态资源
│   │   ├── components/
│   │   │   ├── layout/            # AppShell/Sidebar/TopBar
│   │   │   ├── question/          # QuestionCard/TagList
│   │   │   ├── ai/                # AIGenerationPanel/StreamStatus
│   │   │   ├── upload/            # ImageInput/图片预览/拍照相册入口
│   │   │   └── common/            # EmptyState/ErrorState/Loading
│   │   ├── composables/           # useAuth/useSSE/useImagePicker/usePagination
│   │   ├── router/
│   │   ├── stores/
│   │   ├── styles/                # tokens/arco/global
│   │   ├── types/
│   │   ├── utils/                 # markdown/sanitize/format/error
│   │   └── views/                 # 页面
│   ├── tests/                     # Vitest 单测
│   └── e2e/                       # Playwright
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version            # 3.13
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                  # config/security/logging/errors
│   │   ├── db/                    # engine/session/base
│   │   ├── models/                # SQLAlchemy
│   │   ├── schemas/               # Pydantic
│   │   ├── api/v1/                # routers
│   │   ├── services/              # 业务逻辑
│   │   ├── ai/                    # client/prompts/parser/validator/vision
│   │   └── utils/
│   ├── tests/
│   ├── scripts/                   # seed/dev 脚本
│   ├── fixtures/                  # 合成题目/测试数据
│   ├── data/                      # SQLite 文件（gitignore）
│   └── uploads/                   # 上传文件（gitignore）
├── contracts/                     # 前后端共享契约
│   ├── README.md
│   ├── openapi/                   # 后端导出的 openapi.json
│   └── examples/                  # 合成请求/响应示例
├── deploy/
│   ├── docker-compose.yml         # 生产/演示
│   ├── docker-compose.dev.yml     # 本地依赖（MySQL）
│   ├── nginx.conf
│   ├── .env.example
│   ├── README.md                  # 部署/回滚步骤
│   └── scripts/
├── tools/                         # 本地工具，不上传（gitignore）
│   ├── README.md
│   └── opencode-session-monitor/  # 本地会话/子 agent 监控
├── scripts/                       # 跨前后端的开发脚本（可选）
└── .github/
    ├── workflows/
    │   └── ci.yml
    ├── ISSUE_TEMPLATE/
    └── pull_request_template.md
```

## 3. 目录职责

| 目录 | 放什么 | 不放什么 |
|---|---|---|
| `docs/agent/` | 工程上下文、契约、进度、风险、工作流 | 代码、临时笔记、聊天记录 |
| `docs/product/` | PRD、IA、流程、页面规范、设计 tokens | 实现细节、API 字段定义（放 05） |
| `docs/adr/` | 不可逆/跨模块决策 | 日常小决定 |
| `frontend/src/api/` | Axios 实例、端点函数、请求/响应类型 | 业务组件、页面状态 |
| `frontend/src/components/` | 可复用展示/交互组件 | 页面级数据请求（放 views/composables） |
| `frontend/src/components/common/` | 共享 UI（PageHeader/Empty/Error/Loading/Markdown/Tag） | 业务组件、API 调用 |
| `frontend/src/components/upload/` | 图片上传、预览、手机拍照/相册入口 | 业务 API 编排（放 views/composables） |
| `frontend/src/views/` | 路由页面，负责编排数据与组件 | 大段可复用 UI（拆到 components） |
| `frontend/src/stores/` | 跨页面状态（auth、ui） | 只在一个组件用的局部状态 |
| `frontend/src/composables/` | 可复用逻辑（SSE、分页、异步状态） | 纯展示 |
| `frontend/src/utils/` | 纯函数（markdown、sanitize、format） | 有副作用的业务逻辑 |
| `backend/app/api/v1/` | 路由、参数校验、鉴权、调用 service | SQL、业务规则 |
| `backend/app/services/` | 业务规则、事务、AI 编排 | HTTP 细节 |
| `backend/app/models/` | SQLAlchemy 模型 | 业务逻辑 |
| `backend/app/schemas/` | Pydantic 请求/响应 | ORM 模型 |
| `backend/app/ai/` | LLM 客户端、prompt、解析、校验、DeepSeek 识图 | 路由、DB 查询 |
| `backend/fixtures/` | 合成题目/测试数据 | 真实学生题目/图片 |
| `backend/tests/` | pytest 单测/集成测试 | 真实 LLM 调用 |
| `contracts/` | OpenAPI、请求/响应示例 | 业务逻辑、密钥 |
| `deploy/` | compose、nginx、部署脚本、环境变量模板 | 业务代码 |
| `scripts/` | 跨端开发脚本（seed、检查） | 生产密钥 |
| `.github/` | CI、Issue/PR 模板 | 业务代码 |

## 4. 命名规范

| 类型 | 规范 | 示例 |
|---|---|---|
| Vue 组件 | PascalCase | `QuestionCard.vue`、`AIGenerationPanel.vue` |
| 页面 | `XxxView.vue` | `QuestionListView.vue` |
| composable | `useXxx.ts` | `useSSE.ts` |
| store | `useXxxStore.ts` | `useAuthStore.ts` |
| API 文件 | 领域名 | `questions.ts`、`auth.ts` |
| Python 模块 | snake_case | `question_service.py` |
| Python 类 | PascalCase | `QuestionService` |
| 数据库表 | snake_case 复数 | `generated_questions` |
| API 路径 | 复数、kebab/小写 | `/generated-questions` |
| 环境变量 | UPPER_SNAKE | `LLM_API_KEY` |
| 分支 | `feat/`、`fix/`、`docs/`、`chore/` | `feat/frontend-question-list` |
| 任务 ID | 前缀-三位数字 | `FE-012`、`BE-007` |

## 5. 文件放置决策树

```text
我要新增一个文件
├─ 是文档？
│   ├─ 给 agent/团队看的工程上下文 → docs/agent/
│   ├─ 产品设计 → docs/product/
│   └─ 不可逆技术决策 → docs/adr/
├─ 是前端代码？
│   ├─ 页面 → frontend/src/views/
│   ├─ 可复用 UI → frontend/src/components/<领域>/
│   ├─ HTTP 请求/类型 → frontend/src/api/
│   ├─ 跨页面状态 → frontend/src/stores/
│   ├─ 复用逻辑 → frontend/src/composables/
│   ├─ 纯函数 → frontend/src/utils/
│   └─ 样式/tokens → frontend/src/styles/
├─ 是前后端共享契约？
│   ├─ OpenAPI → contracts/openapi/
│   └─ 请求/响应示例 → contracts/examples/
├─ 是后端代码？
│   ├─ 路由 → backend/app/api/v1/
│   ├─ 业务逻辑 → backend/app/services/
│   ├─ ORM 模型 → backend/app/models/
│   ├─ 请求/响应 schema → backend/app/schemas/
│   ├─ AI 相关 → backend/app/ai/
│   └─ 配置/安全/日志 → backend/app/core/
├─ 是部署/环境？
│   ├─ compose/nginx/部署脚本 → deploy/
│   └─ CI/Issue/PR 模板 → .github/
└─ 是参考材料？
    └─ Resource/（只读，不修改）
```

**不确定时**：先在 `docs/agent/06-file-tree.md` 里补一行说明，再建文件；不要新建顶层目录。

## 6. 不要提交/不要手改

| 路径 | 原因 |
|---|---|
| `frontend/node_modules/`、`frontend/dist/` | 依赖/构建产物 |
| `backend/.venv/`、`__pycache__/`、`.pytest_cache/` | 虚拟环境/缓存 |
| `backend/data/*.db` | 本地数据库 |
| `backend/uploads/` | 用户上传文件 |
| `.env`、`deploy/.env` | 密钥 |
| `Resource/` | 本地只读参考资料；**不上传仓库**（版权/体积） |
| `tools/` | 本地工具（会话监控等）；**不上传仓库** |
| `.omo/` | agent 会话状态；本机使用 |
| `*.log` | 日志 |
| `frontend/src/api/types.ts`（如果由 OpenAPI 生成） | 生成文件；改契约后重新生成 |

> `.gitignore` 必须在 M0 建好；不确定时先跑 `git status` 看有没有敏感文件。

## 7. 根目录文件说明

| 文件 | 作用 | 谁维护 |
|---|---|---|
| `AGENTS.md` | agent 入口、硬性规则、必读顺序 | 霹雳马桶 |
| `README.md` | 项目简介、快速开始、目录说明、演示地址 | 两人 |
| `.gitignore` | 忽略依赖/产物/密钥/数据 | 人机 |
| `.gitattributes` | 统一 LF；Windows 脚本可用 CRLF | 人机 |
| `.editorconfig` | 缩进/编码/换行 | 两人 |
| `docs/README.md` | 文档总索引 | 霹雳马桶 |

### 7.1 Resource 目录约定

- `Resource/` 是**本地只读参考资料**，不提交到 GitHub。
- 仓库里的 `docs/agent/10-resources.md` 保留摘要和引用；需要原文时向霹雳马桶索取，或放团队网盘。
- 新环境 clone 后没有 `Resource/` 是正常的；不要因为文档里的路径找不到就报错。
- 不要把 docx 转成图片/文本后提交；只保留自己写的摘要。

## 8. Windows 开发注意

- 仓库统一 UTF-8；`.gitattributes` 设置 `* text=auto eol=lf`，避免 CRLF 噪声。
- 路径拼接用 `pathlib`（Python）/`node:path`（前端），不要手写 `\`。
- SQLite 文件路径用相对路径 `./data/app.db`，不要写死 `G:\...`。
- Docker Desktop 需要 WSL2；MySQL 容器端口映射到 `127.0.0.1:3306`。
- 项目统一 Python 3.13；用 `uv python install 3.13` + `.python-version` 固定 3.13；不要依赖系统 Python 直接跑。

## 9. 目录变更规则

1. 新增顶层目录：必须更新本文件 + `AGENTS.md` + `docs/README.md`，并在 PR 说明原因。
2. 新增 `frontend/src/components/<领域>/`：在本文件第 3 节补一行职责。
3. 新增后端模块：在 `05-architecture.md` 第 9 节补分层说明。
4. 移动文件：先全局搜索引用，再移动；PR 里单独一个 commit，避免和功能改动混在一起。
5. 删除文件：确认没有引用/测试依赖；删除后在 PR 说明。
