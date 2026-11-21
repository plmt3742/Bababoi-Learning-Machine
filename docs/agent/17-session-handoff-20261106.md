---
owner: 霹雳马桶
last_updated: 2026-11-06
status: active
read_when: 切换会话/交接前端与联调状态；需要知道当前分支、PR、阻塞与下一步
---

# 17 · 会话交接快照（2026-11-06 晚）

> ⚠️ 已过期（2026-11-07）：#38 已关闭；#39/#42/#49/#50/#51 已合并。当前状态见 `docs/agent/00-context.md` 与 `04-todos.md`；FE-027 收口已合入 main。

> 用途：下一位 agent / 新会话先读这一页，再读 00-context、04-todos、05-architecture。
> 当前工作区在 `feat/frontend-fe-026`，**不是 main**。

## 1. 当前 Git 状态

```text
本地分支：
* feat/frontend-fe-026   97b9917  （已 push，跟踪 origin）
  main                   3747bd1  （= origin/main）

远端分支：
  origin/main
  origin/feat/frontend-fe-026
  origin/feat/be-021-generation-segments   （PR #39）
  origin/feat/be-014-image-intake          （PR #40，stacked 在 #39 上）
  origin/docs/be-001-007-status-sync       （PR #8，保留）

worktree：只有主工作区
```

- 当前分支 3 个提交：
  - `aaa919d` feat(frontend): add home navigation and image AI prefill
  - `b5dea9e` feat(backend): enforce generated question type consistency
  - `97b9917` docs(agent): sync FE-026 and API contract v0.4.5
- 工作区有未提交文件：
  - `frontend/src/types/components.d.ts`（Vite 自动生成，27 行新增；如要干净可 `git checkout -- frontend/src/types/components.d.ts`）
  - `docs/adr/ADR-004/005/007`、`docs/agent/08-design-playbook.md` 显示 modified，但 diff 为空（换行符差异）。

## 2. 当前 open PR

| PR | 标题 | base | 状态 | CI | 备注 |
|---|---|---|---|---|---|
| #38 | feat(frontend): FE-026 首页导航 + 图片 AI 初判 + 生成题型硬约束 | `main` | open / clean | ✅ frontend + backend | 已请求 `zhouyuliang0606` review |
| #39 | feat(be-021): 三段并发生成（每段 1 题）+ ADR-006 | `main` | open / clean | ✅ 双绿 | 后端新 PR，131 tests，05 v0.5.1 |
| #40 | feat(be-014): 图片上传 + 鉴权取图 + from-image 多题文本提取 | `feat/be-021-generation-segments` | open / clean | ✅ 双绿 | 后端新 PR，157 tests，**stacked 在 #39** |
| #8 | docs: BE-001~007 状态回写 + 06 后端树 | 旧 main | open / **dirty** | — | 已 request changes；需 rebase/重做，不阻塞产品 |

PR 链接：

- #38 https://github.com/plmt3742/Bababoi-Learning-Machine/pull/38
- #39 https://github.com/plmt3742/Bababoi-Learning-Machine/pull/39
- #40 https://github.com/plmt3742/Bababoi-Learning-Machine/pull/40
- #8 https://github.com/plmt3742/Bababoi-Learning-Machine/pull/8

## 3. 必须先处理的三件事

### 3.1 题型口径冲突（#38 vs #39）

- #38 实现的是**题型硬约束**：生成题必须与原题同题型，不一致重试 1 次后 `AI_INVALID_OUTPUT`。
- #39 实现的是**题型软约束**：prompt 首选同题型，但允许换题型，validator 不强制。
- 两者都使用 `generate_v2`，**同版本号相反语义**，会让 `ai_call_logs` / `generated_questions.prompt_version` 无法区分。
- #39 作者建议 #38 只保留 `frontend/`，后端交给 #39。

需要产品/前端拍板：

- 坚持“相似题题型必须与原题一致” → 让 #39 改硬约束；
- 或接受软约束 → #38 删掉后端硬约束及对应文档表述。

按霹雳马桶之前明确提出的需求，**优先按硬约束处理**。

### 3.2 #40 实际没有返回 AI 初判字段

PR #40 描述说每题返回 `subject` / `chapter` / `difficulty`，但当前分支实际代码没有：

- `backend/app/schemas/image.py::ExtractedQuestionOut` 只有
  `index`、`content_md`、`question_type`、`options`、`blanks`、`has_figure`、`warnings`、`incomplete`。
- `backend/app/ai/validator.py::ExtractedQuestion` 同样没有这三个字段。
- PR #40 的 `docs/agent/05-architecture.md` §7.0 还写着“`subject` 只是提示词背景，不构成出参”。

后果：如果 #40 直接合并，#38 的 FE-026 图片 AI 初判预填会**静默拿不到值**，不报错但不会自动填学科/章节/难度。

需要 #40 在以下位置补齐：

- `schemas/image.py::ExtractedQuestionOut`
- `ai/validator.py::ExtractedQuestion`
- `ai/prompts.py::vision_messages` 的输出 JSON 要求
- 05 §6.8 响应示例
- `test_images_api.py` 断言

### 3.3 合并顺序

#40 的 base 是 #39，不能先合 #40。建议：

```text
1. 先定题型口径
2. #39 修正后合并到 main
3. #40 rebase 到 main、补 subject/chapter/difficulty，再合并
4. #38 rebase 到 main，只保留 frontend + 必要文档（去掉与 #39 重叠的 backend）
```

## 4. 产品闭环现状

| 环节 | 状态 | 缺口 |
|---|---|---|
| 登录/注册 | ✅ | 真实后端可用 |
| 文本错题录入 | ✅ | 真实后端可用 |
| 图片错题录入 | ⚠️ | #40 已实现上传/取图/from-image，但未合且缺 AI 初判字段 |
| AI 分析 | ✅ | 真实任务链路可用 |
| 生成 3 道相似题 | ⚠️ | #39 已实现三段并发，但题型软约束与需求冲突 |
| 练习 | ✅ | 真实后端可用 |
| 统计/薄弱点 | ❌ | BE-013 仍缺 |
| 草稿 | ❌ | BE-018 仍缺 |
| staging/部署 | ❌ | OPS-001/002/005 仍缺；11.14 是硬截止 |
| 演示种子数据 | ❌ | BE-008 仍缺 |

## 5. 验证记录（本会话）

### 前端

- `pnpm lint` ✅
- `pnpm typecheck` ✅
- `pnpm build` ✅
- `pnpm format:check` 仍会因历史未统一格式全仓报错（未做全仓格式化）。

### 后端（本会话在 #38 分支上）

- `uv sync --frozen --group dev` ✅
- `pytest -q` ✅（117 个用例）
- `ruff check app tests` ✅

### 真实后端冒烟（本地 uvicorn + SQLite + `LLM_MOCK=true`）

- `/health`、`/ready`：200
- 注册/登录/`/auth/me`：通过
- 创建错题 → analysis 任务 done
- 生成相似题 → quiz 任务 done，3 题，题型全部为 `solve`（#38 硬约束分支）
- 练习记录 201；重复提交 409 `PRACTICE_DUPLICATE`
- 缺失接口（当时）：`/uploads/images`、`/questions/from-image`、`/drafts/me`、`/stats/overview`、`/settings/ai`

> #40 合并后，图片相关接口会补齐；统计/草稿/BYOK 仍缺。

## 6. 本地环境

- `backend/.env` 已存在（gitignored）：SQLite + `LLM_MOCK=true` + JWT secret。
- `backend/.venv` 已通过 `python -m uv sync` 创建。
- `backend/bababoi.db` 存在，但可能只是空库；先跑 `python -m uv run alembic upgrade head`。
- `frontend/.env.local` **不存在**；接真实后端时创建：

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_USE_MOCK=false
```

然后重启 `pnpm dev`（Vite 只在启动时读 env）。

## 7. 启动/检查命令

```bash
# 后端
cd backend
python -m uv sync --frozen --group dev
python -m uv run alembic upgrade head
python -m uv run uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
pnpm dev
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/ready
```

## 8. 建议下一会话先做的事

1. 读这一页 + `docs/agent/00-context.md` + `04-todos.md` + `05-architecture.md`。
2. 打开 #39 / #40，确认题型口径和 `subject/chapter/difficulty` 缺字段问题。
3. 决定 #38 是否拆成纯前端分支；若拆，保留 `aaa919d`（前端）+ 必要的非冲突文档，去掉 `b5dea9e` 的后端重叠。
4. 合 #39 → rebase #40 到 main 并补字段 → 合 #40 → rebase #38 → 合 #38。
5. 然后推进 BE-013 统计、BE-018 草稿、BE-008 种子、OPS-005 staging。
6. #8 不要直接合；已 request changes，等重做。

## 9. 已知风险

- 图片识别没有真实后端时只能用 mock；#40 合并前不能算真闭环。
- #40 的 `subject/chapter/difficulty` 静默缺失，最危险：前端不报错，但 AI 初判永远为空。
- #39 软约束与产品需求冲突；同版本号 `generate_v2` 语义不一致。
- 11.14 staging 仍无实际部署，是当前最大交付风险。
- 前端无自动化测试（`tests/`、`e2e/` 仍只有 `.gitkeep`）。

## 10. 新会话提示词

```text
先读 docs/agent/17-session-handoff-20261106.md，再读
docs/agent/00-context.md、04-todos.md、05-architecture.md。
当前在 feat/frontend-fe-026；先确认 PR #38/#39/#40 的题型口径与
from-image 的 subject/chapter/difficulty 字段，再做合并顺序决策。
```
