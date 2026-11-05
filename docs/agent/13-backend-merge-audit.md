---
owner: 霹雳马桶
last_updated: 2026-11-05
status: active
read_when: 后端合并审查、CI 设立、M0 收尾、PR 复盘
---

# 13 · 后端合并审查与 CI 方案

> 审查对象：`origin/main @ 18cc663`（后端 BE-001/002/003 合并后的状态）
> 2026-11-05 注：图片交互已由 ADR-004 改为「用户裁剪 + 多题文本提取」，本文中框题 demo/bbox 仅作历史参考。
> 对照基线：`07-workflow.md`、`05-architecture.md` v0.3、`12-backend-alignment.md`
> 结论先行：**内容基本可运行，但合并过程不合规；不建议 revert，建议冻结 main + 修复 forward。**

## 1. 结论摘要

| 维度 | 结论 |
|---|---|
| 代码可运行性 | ✅ `ruff check` 通过；`pytest` 42 passed；迁移 upgrade/downgrade 测试通过 |
| 数据模型 | ✅ 9 张表与 05 v0.3 基本一致；迁移可逆 |
| 认证 | ✅ 注册/登录/me、JWT、bcrypt、限流测试覆盖较完整 |
| 密钥 | ✅ 未发现真实密钥；`.env.example` 均为空占位 |
| 合并流程 | ❌ PR #2/#3/#4 由作者自己合并，**0 review**，9 分钟内连续合并 |
| CI 可信度 | ❌ `frontend` job 是空壳，任何情况都绿；`backend` job 可信 |
| 文档同步 | ❌ `backend/README`、根 README、`04-todos`/`06-file-tree` 与 main 实际状态不一致 |
| 分支管理 | ❌ BE-012 PR #9 base 是 BE-004，不是 BE-006-007；会分叉 |

**建议：保留当前 main，不 revert。** 这批代码是可用资产；回滚会破坏后续 PR 的基点。用一条修复 PR + 分支保护把流程拉回正轨。

## 2. 已合并内容（main）

`main` 比前端分支 `319d0a3` 多 15 个提交，主要包含：

- BE-001：FastAPI 脚手架、`/health`、CORS、request_id 日志、统一错误信封、CI、三种题型 schema
- BE-002：9 张表 + Alembic 初始迁移 + 模型/迁移测试
- BE-003：注册/登录/me + JWT + bcrypt + 登录限流
- 附带：`docs/interaction/frame-adjust-demo.html`（框题交互参考件）

**未合并**（仍在 PR/分支上）：

- PR #7 `feat/be-004-questions`（base main）
- PR #6 `feat/be-005-llm`（base BE-004）
- PR #5 `feat/be-006-007-generation`（base BE-005）
- PR #9 `feat/be-012-practice-records`（**base BE-004，分叉**）
- PR #8 `docs/be-001-007-status-sync`（base main，文档状态）

## 3. 合并规范问题（P0）

### 3.1 PR 全部无 review、作者自合并

PR #2/#3/#4 的 `reviews` 都是 **0**，由 `zhouyuliang0606` 自己合并：

| PR | 创建 | 合并 | Review |
|---|---|---|---|
| #2 BE-001 | 07:24:48 | 07:33:47 | 0 |
| #3 BE-002 | 07:24:49 | 07:33:55 | 0 |
| #4 BE-003 | 07:24:51 | 07:34:02 | 0 |

这违反 `07-workflow.md`：**CI 绿 + 另一个人 review 才能合并**。从结果看，`main` 没有强制 review（或保护规则允许绕过）。

**建议**：

1. 立刻在 GitHub Settings → Branches 给 `main` 开保护：Require PR、Require 1 approval、Require status checks、Dismiss stale approvals、Do not allow bypass。
2. 以后所有 PR 必须由另一个人 review；作者不能自己 merge。
3. 已有 PR #5–#9 也全部 0 review；合并前补 review。

### 3.2 合并方式不是 squash

`main` 上是 merge commit（`Merge pull request #2/#3/#4`），而 `07-workflow.md` 要求 **squash merge**。这导致：

- 每个分支都带一份重复的 `fix(ci)` 提交（`262e243`/`19ef46c`/`f76df37` 等）；
- 历史噪音，后续 blame/revert 成本变高。

**建议**：后续 PR 统一 squash merge；已合并的历史不再重写。

### 3.3 PR base 与叠放关系不一致

PR #3/#4 的正文写着“base 请选上一个分支”，但实际 GitHub base 是 `main`。虽然内容没坏，但：

- 评审 diff 边界不清晰；
- 三个 PR 同时打开、连续合并，事实上绕过了逐层 review。

**建议**：stacked PR 必须显式 base 到上一个分支；合并顺序按 stack 从底到顶。

### 3.4 未合并 PR 的分叉

- PR #9（BE-012）base 是 `feat/be-004-questions`，没有包含 BE-005/006-007；而 BE-005/006-007 已改了同样的 `main.py`、`questions.py`、`schemas/question.py`、`tests/conftest.py`。
- 如果先合 #5 再合 #9，冲突几乎必然；如果先合 #9，再合 #5，同样冲突。

**建议顺序**：

```text
#7 BE-004 (base main)
  → #6 BE-005 (base BE-004)
    → #5 BE-006-007 (base BE-005)
      → 把 #9 BE-012 rebase 到最新 main / BE-006-007 后再开/更新 PR
        → #8 docs 状态同步最后合
```

## 4. 代码/配置问题

### 4.1 CI 前端 job 是空壳（P0）

`.github/workflows/ci.yml:29-50`：

```yaml
frontend:
  ...
  - name: Detect frontend scaffold
    ...
  - name: TODO(FE-001)
    if: steps.detect.outputs.ready == 'true'
    run: echo "TODO(FE-001): 装依赖并跑 pnpm lint / typecheck / build"
```

即使 `frontend/package.json` 存在，也只是 echo 一行 TODO，**永远绿**。GitHub 上 frontend check 5–9 秒完成，就是证据。

**影响**：CI 绿不代表前端可构建；FE-001 后如果忘了改 CI，前端坏代码也能合进 main。

**建议**：FE-001 的第一个 PR 就把 frontend job 改成真实命令（见第 6 节）。

### 4.2 `/health` 不检查数据库（P1）

`backend/app/api/v1/health.py:13-18`：

```python
"db": "configured" if settings.database_url else "not_configured"
```

`settings.database_url` 默认为空，而 `db/session.py` 实际会 fallback 到 SQLite。所以：

- BE-002 已接数据库，`/health` 仍显示 `not_configured`；
- 即使 `.env` 填了 URL，也只检查“字符串非空”，不检查能否连接。

`backend/tests/test_health.py:14-20` 还把这个旧行为写成了断言，修复时要一起改。

**建议**：`/health` 执行 `SELECT 1`（或 `/ready` 单独做 DB/LLM 配置检查），失败返回 503；测试改成“DB 可用/不可用”两种。

### 4.3 MySQL 连接串写错（P1）

`backend/.env.example:5`：

```text
# 本地：sqlite:///./bababoi.db   生产：mysql+aiomysql://user:pass@host/bababoi
```

但后端是 **sync SQLAlchemy**（`create_engine`），`pyproject.toml` 也没有 `aiomysql`/`pymysql`。照抄这行会启动失败。

**建议**：sync-first 下改成 `mysql+pymysql://...`，并在 `pyproject.toml` 加 `pymysql`；或者明确切换 async 栈（不推荐现在改）。

### 4.4 文档状态不一致（P1）

- `backend/README.md:5` 仍写“状态：目录骨架。脚手架任务 BE-001”；
- 根 `README.md:47` 仍写“数据库与迁移在 BE-002 接入”；
- `docs/agent/04-todos.md:76-82` 的 BE-001/002/003 仍是 `TODO`；
- `docs/agent/06-file-tree.md` 仍把 `backend/` 写成骨架。

PR #8 是来修这些的，但它把 BE-004~007 标成 `DONE`，而 #5/#6/#7 还没合。**不要在代码 PR 合并前合 #8**，否则 main 文档会声称未合的功能已完成。

**建议**：代码 PR 全部合并后，更新 #8 为真实状态再合；或者先合一个只改 BE-001~003 的小 docs PR。

### 4.5 格式化未纳入 CI（P2）

`uv run ruff check app tests` 通过；但 `uv run ruff format --check app tests` 报 **24 files would be reformatted**。当前 CI 只跑 `ruff check`，不跑 format。

**建议**：决定是否把 `ruff format --check` 加入 CI；如果加，先跑一次 `uv run ruff format app tests` 单独提交格式化 PR，不要混在功能 PR 里。

### 4.6 限流按 `request.client.host`（P2）

`backend/app/api/v1/auth.py:15-16` 取 `request.client.host`。部署到 nginx 后，所有请求的 client IP 都是 nginx 地址，登录失败限流会误伤所有用户。

**建议**：只信任可信代理的 `X-Forwarded-For`（配置 `TRUSTED_PROXIES`），或明确记录“单机直连有效，反代后需改”。

### 4.7 未预期异常没有日志（P2）

`backend/app/core/errors.py:94-100` 的 `handle_unexpected` 注释说“细节进日志”，但函数里没有 `logger.exception`。500 响应只有一句“服务内部错误”，排查时没有堆栈。

**建议**：在 handler 里 `logger.exception("unhandled error rid=%s", request.state.request_id)`，响应仍不暴露堆栈。

### 4.8 非 404 的 HTTPException 一律映射为 VALIDATION_ERROR（P2）

`backend/app/core/errors.py:84-91`：405/403 等都会被标成 `VALIDATION_ERROR`。前端按 code 分支时会误判。

**建议**：按状态码映射：404→NOT_FOUND、405→METHOD_NOT_ALLOWED、403→FORBIDDEN、其余→VALIDATION_ERROR/INTERNAL_ERROR；错误码只加不改。

### 4.9 `uv sync` 未加 `--frozen`（P2）

CI 用 `uv sync --group dev`，如果 `uv.lock` 与 `pyproject.toml` 不一致，CI 会静默更新 lock，而不是失败。

**建议**：CI 改 `uv sync --frozen --group dev`，保证 lockfile 是提交过的那份。

### 4.10 `docs/interaction/frame-adjust-demo.html` 未入索引（P3）

BE-001 把一个 882 行的框题交互 demo 放进 `docs/interaction/`，但 `docs/README.md` 没有索引。它不是契约，作为参考没问题；如果保留，建议在 `docs/README.md` 加一行，或移到 `docs/product/drafts/` 统一管理。

## 5. 已验证通过的部分

- `python -m uv run ruff check app tests` → All checks passed
- `python -m uv run pytest` → 42 passed
- `feat/be-006-007-generation` 独立测试 → 72 passed
- `feat/be-012-practice-records` 独立测试 → 58 passed
- 迁移 `upgrade head` / `downgrade base` 测试通过
- 9 张表与 05 v0.3 基本一致
- `.env.example` 无真实密钥
- JWT/bcrypt/错误信封/请求 ID 测试覆盖较好

## 6. CI 设立方案

### 6.1 目标

**PR 上必须自动回答三件事**：

1. 后端能不能装、能不能 lint、能不能测、迁移能不能跑；
2. 前端能不能装、能不能 lint/typecheck/build/test；
3. 契约（OpenAPI/类型）有没有漂移。

### 6.2 建议的 `ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
          enable-network-caching: true
      - run: uv sync --frozen --group dev
      - run: uv run ruff check app tests
      - run: uv run ruff format --check app tests   # 若决定强制格式化
      - run: uv run pytest
        env:
          LLM_MOCK: "true"

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm typecheck
      - run: pnpm build
      - run: pnpm test
```

> 在 FE-001 还没有 `package.json` 的过渡期，frontend job 可以先保留 detect guard；FE-001 合并当天必须换成真实命令，并删除 TODO echo。

### 6.3 CI 分阶段

| 阶段 | 内容 |
|---|---|
| 现在 | 后端 `ruff check` + `pytest` + `--frozen`；前端 guard；CI 不调真实 LLM |
| FE-001 后 | 真实 frontend job（pnpm install/lint/typecheck/build/test） |
| BE-009 后 | 导出 OpenAPI 并与 `contracts/openapi/openapi.json` diff |
| M1 后 | 加 MySQL service job：`alembic upgrade head` + 核心 API 冒烟 |
| 部署后 | CD 单独做 staging 部署，不混在 CI |

### 6.4 分支保护（必须在 GitHub Settings 配）

- Require a pull request before merging
- Require approvals: 1
- Dismiss stale pull request approvals
- Require status checks: `backend`、`frontend`
- Require branches to be up to date
- Do not allow bypassing the above settings
- Restrict who can push to `main`（只允许 PR 合并）

> 代码里的 `ci.yml` 只能“检查”，不能“阻止合并”；阻止合并靠 branch protection。

## 7. 回溯与修复建议

### 7.1 不建议 revert

PR #2/#3/#4 的内容是可用资产；revert 会让 main 回到文档骨架，并让 BE-004+ 分支失去基点。**保留 main，修复 forward。**

### 7.2 建议动作

| 优先级 | 动作 | 负责人 |
|---|---|---|
| P0 | 开启 main 分支保护；禁止作者自合并 | 两人 |
| P0 | 补 review PR #2/#3/#4（事后 review 记录） | 霹雳马桶 |
| P0 | 修 CI frontend job（FE-001 同步） | 霹雳马桶 |
| P1 | `/health` 加 DB 连通性；改测试 | 人机 |
| P1 | `.env.example` 改 `mysql+pymysql` + 加依赖 | 人机 |
| P1 | 更新 backend/README、根 README、04/06 状态 | 人机 / 霹雳马桶 |
| P1 | PR #9 rebase 到 BE-006-007/main；#8 等代码合并后再合 | 人机 |
| P2 | 加 `ruff format --check` + 格式化 PR | 人机 |
| P2 | 反代 IP / 异常日志 / HTTPException 映射 | 人机 |

## 8. 给后端的同步文本（可直接发）

```text
后端合并审查结果（main @ 18cc663）：

1. 内容整体可运行：ruff check 通过、pytest 42 passed、迁移可逆、9 张表与 05 基本一致；不准备 revert。
2. 但流程不合规：PR #2/#3/#4 都是 0 review、作者自己合并，9 分钟内连续合入；main 需要立刻开分支保护（Require PR + 1 approval + CI + no bypass）。
3. CI 的 frontend job 现在是空壳：有 package.json 也只 echo TODO，永远绿；FE-001 时必须改成真实 pnpm lint/typecheck/build/test。
4. 需要修：
   - /health 不检查 DB（settings.database_url 空时永远 not_configured；测试还写死了这个旧行为）
   - .env.example 的 mysql+aiomysql 与 sync SQLAlchemy 不匹配；应改 mysql+pymysql 并加依赖
   - backend/README、根 README、04-todos/06-file-tree 状态过期；PR #8 先别合，等代码 PR 合完再改真实状态
   - PR #9 (BE-012) base 是 BE-004，不是 BE-006-007；需要 rebase 后再合
   - CI 建议加 uv sync --frozen；ruff format --check 目前 24 个文件会红，决定是否强制
   - 反代后 login 限流的 request.client.host 会变成 nginx IP；需要可信代理/X-Forwarded-For
   - 未预期异常 handler 没有 logger.exception；500 没有堆栈日志
5. 建议合并顺序：#7 BE-004 → #6 BE-005 → #5 BE-006-007 → rebase #9 BE-012 → #8 docs。
6. 以后 PR：base 显式指向上一个 stack 分支；squash merge；作者不自合；至少 1 人 review。
```

## 9. 本轮审查命令记录

```text
git fetch --prune --all
git log --oneline --graph --decorate --all -30
git diff --stat 319d0a3..origin/main
python -m uv sync --group dev
python -m uv run ruff check app tests        # All checks passed
python -m uv run pytest                      # 42 passed
python -m uv run ruff format --check app tests  # 24 files would be reformatted
# 分支独立验证
feat/be-006-007-generation: 72 passed
feat/be-012-practice-records: 58 passed
```

## 10. 未合并分支 review

| 分支 / PR | 内容 | 验证 | 结论 |
|---|---|---|---|
| PR #7 `feat/be-004-questions` | 错题 CRUD + 标签/搜索 | 随 BE-006 分支通过 | 基本可用；有 4 个契约缺口 |
| PR #6 `feat/be-005-llm` | LLM 客户端 + Prompt + 解析/校验 | 随 BE-006 分支通过 | mock 可测；真实调用需 Key |
| PR #5 `feat/be-006-007-generation` | 队列 worker + 分析/生成/任务接口 | **72 passed** | 队列逻辑可用；生成质量校验和任务终态有缺口 |
| PR #9 `feat/be-012-practice-records` | 练习记录 + 防重复 | **58 passed** | 接口可用；base 错、掌握状态未接 |
| PR #8 `docs/be-001-007-status-sync` | 文档状态 | 仅文档 | **暂缓**，等代码 PR 合完 |

### 10.1 BE-004（PR #7）

- `QuestionCreate` / `QuestionUpdate` 没有 5000 字上限；05 写的是题干 ≤5000。
- 搜索只查 `content_md`，没有查知识点标签；PRD 写的是“题干与知识点标签”。
- `PATCH /questions/{id}` 没有 `mastery_status`（对应确认单 B-5）。
- `analysis` 允许任意 dict，没有按 `AnalysisResult` 校验；编辑分析后可能写入坏结构。

### 10.2 BE-005（PR #6）

- `DeepSeekClient` 的 `timeout` 用的是 `recognize_client_timeout_s`（90s），但 05 规定后台任务 120s；`task_hard_timeout_s` 目前没有被使用。
- `PROMPT_VERSION = "v0"`，与 05 的 `analyze_v1` / `generate_v1` 命名不一致；不影响运行，但日志/排查口径不统一。
- 没有使用 JSON mode；目前靠 prompt + parser，真实模型下需要实测稳定性。

### 10.3 BE-006/007（PR #5）

- `TaskOut` 没有 `question_id`（确认单 B-8 已提出）；任务中心跨题展示会缺字段。
- `task_service.get_owned_task` 用 `NOT_FOUND`，而 05 错误码表有 `TASK_NOT_FOUND`；二者需要统一。
- `_apply_quiz` 每次成功都追加 3 道题；任务完成后再次 `POST /generate` 会变成 6 道，而不是替换旧组。需要“替换旧组”或“只允许一次”的明确规则。
- `_apply_analysis` / `_apply_quiz` 不在 `execute_task` 的 try/except 内；写库异常会让任务停在 `running`，直到进程重启才被 `reset_stale_running` 放回队列。
- `validator.validate_quiz` 只校验数量/题型/非空；05 要求的“不与原题高度重复、不依赖图片、LaTeX 成对、长度限制”尚未实现。
- `task_service.enqueue` 的去重键是 `question_id + stage`，没有包含 `target_index`；单题重新生成上线前需要补。

### 10.4 BE-012（PR #9）

- PR base 是 `feat/be-004-questions`，不是 `feat/be-006-007-generation`；与 BE-005/006-007 修改了同一批文件，直接合并会冲突。
- `practice_service.create` 不更新 `questions.mastery_status`；确认单 B-5 需要先定规则。
- 60 秒防重复是“先查再插”，并发请求仍可能插入两条；MVP 可接受，但要在风险里记录。
- `PRACTICE_DUPLICATE` 只在 BE-012 分支；main 的 05 还没加，需要在合入时同步。

### 10.5 PR #8 文档状态

PR #8 把 BE-004~007 标成 `DONE`，但 #5/#6/#7 还没合。**不要先合 #8**；否则 main 文档会声称未合功能已完成。等代码 PR 合完后再更新真实状态。

## 11. 对《前端确认表-20261105》的回复口径

### A. BE-012 练习记录

1. **提交作答**：接受 `POST /practice-records` + 201；`is_correct` 由前端自评传入，后端不判分。
2. **重复点击**：60 秒窗口够用；UI 收到 `409 PRACTICE_DUPLICATE` 用轻提示“刚提交过”，不弹错误窗。
3. **作答历史**：`GET /practice-records?generated_question_id=` 够用；练习页/详情页回显不需要再加 `question_id` 过滤。
4. **用时**：从“题目卡出现在练习页/开始作答”起算；切后台不暂停，超过 3600 按 3600 封顶。

### B. 冻结前契约点

5. **掌握状态**：选 **a) PATCH 可改**。把 `mastery_status` 加进 `PATCH /questions/{id}` 的可改字段；前端自评后顺手 PATCH。自动流转规则（答对 N 次→reviewing）留到 P1，不在 11-08 冻结前发明。
6. **生成题列表**：前端只用 `GET /questions/{id}?include=generated`；请把 05 里的独立端点 `/questions/{id}/generated` 删掉，避免两套取法。
7. **任务进度**：P0 用 `GET /tasks?question_id=` 轮询（1.5s 可接受）；SSE 排 M1 之后，05 里把 SSE 从 P0 改为 P1/后续。
8. **TaskOut 加 `question_id`**：同意，随 PR #5 一起推；这是任务中心跨题展示必需字段。
9. **新增错误码**：接受 `NOT_FOUND`、`AUTH_RATE_LIMITED`、`PRACTICE_DUPLICATE`；FE-004 错误归一化按 code 分支处理，05 补 `PRACTICE_DUPLICATE`。
10. **生成题字段**：`model` / `prompt_version` 不展示给用户，前端忽略但保留字段；`difficulty` 可展示，`validation_status` 仅内部用。

### C. 时间点与合并

11. 以上 5/6 两条按 11-07 前回复；本文件即回复。
12. BE-012 的 PR 实际是 **#9**（不是 #12），base 当前是 BE-004；合并前必须 rebase 到 BE-006-007/main。顺序：**#7 → #6 → #5 → rebase #9 → #8**。
