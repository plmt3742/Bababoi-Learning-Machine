---
owner: 霹雳马桶
last_updated: 2026-11-06
status: active
read_when: 切换会话、换 agent、让新 agent 接手任务时
---

# 11 · 新会话交接（Agent Handoff）

> 目标：让一个新 agent 在 **3 分钟内**知道“项目是什么、现在到哪、我要做什么、不能做什么”，而不是把 `docs/` 全读一遍。

## 0. 当前交接状态（2026-11-06，origin/main @ 7ee6029）

- **`main`**：`7ee6029`（M0 收尾；前端页面全部完成；后端核心闭环已合）
- **已合后端**：BE-001/002/003 + follow-up（#14）、BE-004（#7）、BE-005（#6）、BE-006/007（#5）、BE-012（#9）
- **后端 open PR**：仅 **#8 docs**（基于旧 main，状态很可能已被 #26/#31/#36 覆盖；建议关闭或缩成 `backend/README.md`）
- **后端 open issue**：
  - **#13 BE-014 图片录入 v2**：`/uploads/images` + `/questions/from-image` 尚未实现，是图片识别真联调的唯一阻塞
  - **#32 BE-020 用户自带 AI Key**：`GET/PUT/DELETE /settings/ai` + 加密存储 + SSRF 白名单
  - **#11 BE-001~003 follow-up**：主体已由 #14 修复；剩 docs/README、ruff format、MySQL 实跑
- **前端已合**：FE-001~024 全部页面（#16~#21/#23~#25/#28~#30/#34/#35），含：
  - 首页 `HomeView`（#34）
  - 个人设置 + AI API Key（BYOK，mock；#35，ADR-007）
  - 图片录入 + 多题条目（#29，mock；等 BE-014）
  - 三段并发 UI（#28，兼容旧 `task_id`；等 ADR-006）
  - 草稿双写 + 可访问性（#30，mock；等 BE-018）
  - 练习（#23）、统计（#24，mock；等 BE-013）、三题型编辑器（#25）
- **前端剩余**：FE-017 的 768px 宽度与完整键盘细节；真接口联调
- **管理端**：ADR-005 已定 `admin/` 为 P1 内部运维台，不进入 11.29 演示；当前仅占位
- **PRD**：`docs/prd` 已删除；v0.8 归档为 `docs/product/PRD-v0.8-reference.md`；v0.9 待合并
- **图片录入 v2（正式决策）**：用户裁剪 → 多题文本提取（①②…）→ 逐条确认 → 分析/答案/解析 → 选择 1–3 道生成；不做 bbox/框题；见 ADR-004 / issue #13
- **BYOK（ADR-007）**：Key 只提交后端加密存储；前端不落 localStorage/Pinia、不回显完整值；P1，不进入 11.29 演示关键路径
- **下一步顺序**：
  1. 后端 **BE-014 图片识别**（最高优先；前端 FE-016/021 已就绪）
  2. 后端 **BE-018 草稿 / BE-013 统计 / BE-020 BYOK**
  3. 后端 **ADR-006 三段并发**（新 PR，base=main）
  4. 前端 **FE-017** 768/键盘收尾 + 真接口联调
  5. M0 验收、部署 staging、PRD v0.9
- **本地启动**：
  - 前端：`cd "G:\AIworkspace\opencode\BababoiLearningMachine\frontend"` → `pnpm dev`（PowerShell 不要用 `cd /d`）
  - 开发模式默认 mock；演示账号 `student01 / password123`
  - 后端：`cd backend` → `uv sync` → 配置 `.env`（`JWT_SECRET` ≥32 字节、`LLM_MOCK=true`）→ `uv run alembic upgrade head` → `uv run uvicorn app.main:app --reload`
  - 父目录 `G:\AIworkspace\opencode\pnpm-workspace.yaml` 已改名为 `.bak-20261106`，避免 pnpm 把父项目当 workspace 根；不要恢复，除非处理父项目
- **不要做**：不要 revert 已合后端；不要先合 PR #8；不要绕过 PR review/CI；不要恢复 bbox/框题；不要在前端存 AI Key；不要直接合 main
- **分支规则**：所有开发（含前端/文档）从 `main` 开短分支 + PR；合并前等用户确认。

### 0.1 下一个会话建议直接接的任务

1. **后端 BE-014（最高优先）**：实现 `POST /uploads/images` + `POST /questions/from-image`；契约见 `docs/agent/15-backend-sync-20261106.md` §3 和 issue #13。
2. **后端 BE-018 / BE-013 / BE-020**：草稿、统计、用户 AI Key；前端对应页面已按 mock 完成。
3. **后端 ADR-006 三段并发**：新 PR base=main；前端 FE-023 已兼容旧 `task_id`。
4. **前端 FE-017**：768px + 完整键盘细节；之后把 `VITE_USE_MOCK=false` 做真接口联调。
5. **M0 收尾**：`03-page-specs.md`、`05` 冻结、`deploy/docker-compose.dev.yml`、M0 验收、产品评审同步。

## 1. 最小启动提示词（复制即用）

```text
你是 Bababoi Learning Machine 项目的开发 agent。请先按顺序读：
1. AGENTS.md
2. docs/agent/00-context.md
3. docs/agent/04-todos.md
4. docs/agent/05-architecture.md 的「0. 速览」「5. 数据模型」「6. API 契约」

读完不要立刻写代码。先用 5 行总结：
- 项目一句话
- 当前阶段/里程碑
- 你理解的任务 ID 与目标
- 关键约束（技术栈/不做什么）
- 你看到的最大风险

然后给我一个 3–5 步计划，等我确认后再动手。

当前任务：<任务 ID + 一句话>
范围：<只改哪些文件/模块>
约束：<技术栈/不做什么/验收标准>
截止：<日期>
```

## 2. 角色专用提示词

### 2.1 前端任务

```text
你是本项目前端 agent（Vue 3 + Vite + TypeScript + Arco Design Vue）。
先读：AGENTS.md → docs/agent/00-context.md → docs/agent/04-todos.md → docs/agent/05-architecture.md「0/6.8/7/8 节」→ docs/agent/06-file-tree.md → docs/product/03-page-specs.md + 07-page-drafts.md + 08-interaction-map.md。

任务：<FE-xxx>。
只改 frontend/ 下与任务相关的文件；不要改后端/数据库/Resource。
不要直接 push/merge `main`；完成后开 PR，等用户确认后再合并。
当前状态：FE-001~024 页面已完成；优先 FE-017（768/键盘）与真接口联调。图片/统计/草稿/BYOK 页面当前走 mock，等 BE-014/BE-013/BE-018/BE-020 后再切真实接口。
页面结构/交互参照 `07-page-drafts.md` / `08-interaction-map.md`；**视觉唯一基准是 `calm-academic/index.html`**（顶部 appbar + 1140px 纸面 frame，无侧边栏）。图片 v2 与原型冲突时以 ADR-004 / 05 v0.4 为准。
视觉语言以 `04-design-system.md` 的第一/第二原则 + §1.2 Calm 定稿为准：**可读性优先、整体使用流畅**；不为视觉牺牲题干/公式可读性和主操作路径。
接口以 docs/agent/05-architecture.md 为准；没有的接口先用 Mock，不要自己发明字段。
图片录入按 v2：用户裁剪 → 多题文本提取（①②…）→ 逐条确认 → 分析/答案/解析 → 选择 1–3 道生成；不做 bbox/框题。
必须覆盖 cropping/uploading/extracting/confirming_items/editing/saving/error 等状态；AI 页面加 partial/retry。
完成后跑 pnpm lint / pnpm typecheck / pnpm build，并在 PR 里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.2 后端任务

```text
你是本项目后端 agent（Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic）。
先读：AGENTS.md → docs/agent/00-context.md → docs/agent/04-todos.md → docs/agent/05-architecture.md「0/5/6/7/9 节」→ docs/agent/06-file-tree.md → docs/agent/09-risks.md 的数据库/AI 部分。

任务：<BE-xxx>。
只改 backend/ 下与任务相关的文件；数据库 schema 最终由人机确认，不要擅自改字段/迁移。
AI 调用必须服务端；LLM 测试用 mock，不花真实额度。
接口/字段/错误码必须与 05 一致；改了就先更新 05 和 OpenAPI。
当前最高优先：**BE-014 图片文本提取**（issue #13，契约见 `15-backend-sync-20261106.md` §3）；之后 BE-018 草稿、BE-013 统计、BE-020 BYOK、ADR-006 三段并发。
图片录入按 v2：`from-image` 返回 `questions[]`（1..N），不做 bbox/candidates；用户裁剪后上传；确认后逐条 `POST /questions`。
完成后跑 uv run ruff check / uv run pytest，并在 PR 里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.3 设计/原型任务

```text
你是本项目产品设计 agent。先读：AGENTS.md → docs/agent/00-context.md → docs/agent/01-project.md → docs/agent/08-design-playbook.md → docs/product/README.md。

任务：<DS-xxx>。
只产出设计文档/线框/页面规范，不写业务代码。
目标用户是大学理科生；输入方式有文本和图片（电脑上传 / 手机拍照或相册）。
必须覆盖 AI 状态：cropping/uploading/extracting/confirming_items/analyzing/generating/validating/partial/error；必须有空/错/loading。
不要设计 P2 功能；不要做像素级高保真；11.7 后不再大改。
先复述用户/闭环/页面清单，再开始画。
```

### 2.4 Debug 任务

```text
你是本项目 debug agent。先读：AGENTS.md → docs/agent/09-risks.md 对应条目 → docs/agent/05-architecture.md → 相关代码。

现象：<复现步骤/期望/实际/环境/日志>
先定位根因，不要随机改。一次只改一个假设；每轮说明“改了什么/为什么/怎么验证”。
不要删除失败测试；不要用 as any/@ts-ignore 掩盖类型错误。
修完补一个能复现的测试，并跑相关测试/构建。
```

### 2.5 Review 任务

```text
你是本项目 review agent。先读：docs/agent/07-workflow.md「Code Review 清单」+ docs/agent/05-architecture.md。

审查范围：<PR/commit/diff>。
只看：逻辑/边界、权限、密钥、API 契约、N+1、前端四态、测试、目录规范。
不要改代码；输出按 P0/P1/P2 分级，每条给文件/行号/建议。
```

## 3. 交接时必须提供的信息

| 项 | 示例 | 为什么 |
|---|---|---|
| 任务 ID | `FE-016` | agent 能在 `04-todos.md` 找到验收标准 |
| 一句话目标 | “图片录入支持电脑上传 + 手机拍照/相册” | 防止 agent 自己扩大范围 |
| 范围 | “只改 `frontend/src/components/upload/` 和录入页” | 防止乱改 |
| 明确不做 | “不改后端、不做 OCR、不做批量上传” | 防止范围蔓延 |
| 验收标准 | “桌面/手机入口可用；识图失败可改文本” | agent 知道何时停 |
| 相关文件 | 页面/接口/设计稿链接 | 减少搜索 |
| 已知风险 | “Arco Upload 没有 capture” | 避免踩坑 |
| 截止 | 11.14 / 11.21 | 决定取舍 |

## 4. 让 agent 先复述，再动手

新会话不要直接说“开始写”。先让它回答：

1. 项目一句话是什么？
2. 当前阶段/截止是什么？
3. 你的任务 ID/目标/验收标准是什么？
4. 你准备读/改哪些文件？
5. 你最大的不确定是什么？

如果它答错，先纠正，再让它写。**复述比“好的，我来做”可靠得多。**

## 5. 不要让 agent 做的事

- 不要修改 `Resource/`（只读、且不上传仓库）。
- 不要提交 `.env`、API Key、JWT Secret、数据库密码。
- 不要在前端调用 LLM。
- 不要扩大 P0 范围；不要加 OCR/知识图谱/训练。
- 不要凭记忆写 API；以 `05-architecture.md` / OpenAPI 为准。
- 不要删除失败测试来“通过”。
- 不要一次把 `docs/` 全读；按 `docs/agent/README.md` 的加载策略读。
- 不要新建顶层目录；按 `06-file-tree.md` 放文件。

## 6. 交接检查

- [ ] `AGENTS.md` 存在且是最新。
- [ ] `00-context.md` 的“当前阶段/下一步”是最新。
- [ ] `04-todos.md` 有任务 ID/负责人/验收标准/状态。
- [ ] `05-architecture.md` 的 API/数据模型与代码一致（或明确标注 draft）。
- [ ] 相关风险在 `09-risks.md` 有记录。
- [ ] 密钥不在仓库；`Resource/` 已 gitignore。
- [ ] 新 agent 能本地启动前后端（或知道怎么启动）。

## 7. 示例：M0 前端脚手架交接

```text
你是本项目前端 agent（Vue 3 + Vite + TypeScript + Arco Design Vue）。
先读 AGENTS.md、docs/agent/00-context.md、docs/agent/04-todos.md、docs/agent/05-architecture.md「0/6/8 节」、docs/agent/06-file-tree.md。

任务：FE-001 前端脚手架。
目标：在 frontend/ 初始化 Vue3+Vite+TS+Arco+Router+Pinia+ESLint+Prettier，pnpm dev 可跑，/health 代理到后端。
范围：只改 frontend/；不要写业务页面；不要改后端。
约束：Arco 2.59.x；Vue 3.4 或 3.5 先 spike；不引入 Tailwind；不提交 .env。
验收：pnpm install / pnpm dev / pnpm build 通过；README 更新启动命令。
先复述任务、计划、风险，等我确认再写。
```

> 核心：**任务 ID + 一句话目标 + 明确不做 + 验收标准 + 先复述**。这五样给全，agent 基本不会跑偏。
