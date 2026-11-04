---
owner: 林敬翔
last_updated: 2026-11-04
status: active
read_when: 切换会话、换 agent、让新 agent 接手任务时
---

# 11 · 新会话交接（Agent Handoff）

> 目标：让一个新 agent 在 **3 分钟内**知道“项目是什么、现在到哪、我要做什么、不能做什么”，而不是把 `docs/` 全读一遍。

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
先读：AGENTS.md → docs/agent/00-context.md → docs/agent/04-todos.md → docs/agent/05-architecture.md「0/6/8 节」→ docs/agent/06-file-tree.md → docs/product/03-page-specs.md。

任务：<FE-xxx>。
只改 frontend/ 下与任务相关的文件；不要改后端/数据库/Resource。
接口以 docs/agent/05-architecture.md 为准；没有的接口先用 Mock，不要自己发明字段。
必须覆盖 loading/empty/error/success；AI 页面加 partial/retry。
完成后跑 pnpm lint / pnpm typecheck / pnpm build，并在 PR 里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.2 后端任务

```text
你是本项目后端 agent（Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic）。
先读：AGENTS.md → docs/agent/00-context.md → docs/agent/04-todos.md → docs/agent/05-architecture.md「0/5/6/7/9 节」→ docs/agent/06-file-tree.md → docs/agent/09-risks.md 的数据库/AI 部分。

任务：<BE-xxx>。
只改 backend/ 下与任务相关的文件；数据库 schema 最终由周彧良确认，不要擅自改字段/迁移。
AI 调用必须服务端；LLM 测试用 mock，不花真实额度。
接口/字段/错误码必须与 05 一致；改了就先更新 05 和 OpenAPI。
完成后跑 uv run ruff check / uv run pytest，并在 PR 里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.3 设计/原型任务

```text
你是本项目产品设计 agent。先读：AGENTS.md → docs/agent/00-context.md → docs/agent/01-project.md → docs/agent/08-design-playbook.md → docs/product/README.md。

任务：<DS-xxx>。
只产出设计文档/线框/页面规范，不写业务代码。
目标用户是大学理科生；输入方式有文本和图片（电脑上传 / 手机拍照或相册）。
必须覆盖 AI 状态：vision/analyzing/generating/validating/partial/error；必须有空/错/loading。
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
