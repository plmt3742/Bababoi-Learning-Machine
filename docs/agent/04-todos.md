---
owner: 霹雳马桶
last_updated: 2026-11-10
status: active
read_when: 每天开工领取任务；每天收工更新状态；周会同步进度
---

# 04 · 待办清单

## 0. 使用规则

- 任务状态以本文件 + GitHub Issues 为准；**不要只在聊天里说“做完了”**。
- 领取任务时把状态改成 `DOING`，完成改成 `DONE`，被卡住改成 `BLOCKED` 并写原因。
- 新任务必须写清：**ID、负责人、优先级、依赖、验收标准**。没有验收标准的任务不允许进 P0。
- 任务超过 1 天没动静，在每日同步里说明；超过 2 天，重新拆小或换人。
- 优先级：`P0` 演示必须；`P1` 有余力就做；`P2` 明确不做/未来。
- 任务 ID 前缀：`DS` 设计、`FE` 前端、`BE` 后端、`OPS` 部署、`SH` 共同。

### 任务模板

```text
ID:
标题:
负责人:
优先级:
依赖:
验收标准:
状态: TODO | DOING | DONE | BLOCKED
备注:
```

## 1. 当前冲刺：M0（11.4–11.7）

**目标**：产品设计 + 技术选型 + 仓库骨架，11.7 24:00 前全部可展示。

> 当前同步（2026-11-07）：main 已合 #39（BE-021 三段并发 + ADR-006）、#42（BE-014 图片识图）、#49（FE-026 纯前端）、#50（测试控制台）、#51（FE-027 收口）；#38 已关闭并由 #49 替代。FE-027 已完成：题目编辑、题型开关、18 号识图口径、Vitest、PRD 清理。后端 follow-up：#43 BE-025 三题型 PATCH、#44 BE-026 生成偏好、#45 BE-013 统计、#46 BE-018 草稿、#32 BE-020 BYOK、#47 BE-024 两步识图、#48 seed/OpenAPI/staging。

### 1.1 设计（霹雳马桶 + 人机共同主导，我想抓住风的影子评审）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| DS-001 | 填一页纸 PRD | 霹雳马桶 + 人机 | P0 | 无 | `docs/product/01-prd-lite.md` 有大学理科用户、问题、闭环、P0/P1/P2、非目标、指标 | DONE |
| DS-002 | 信息架构 + sitemap | 霹雳马桶 + 人机 | P0 | DS-001 | sitemap 覆盖登录/首页/录入/编辑（三种题型）/任务中心/列表/详情/练习/统计（P1）；导航层级清晰 | DONE |
| DS-003 | 3 条核心用户流程 | 霹雳马桶 + 人机 | P0 | DS-001 | 用 Mermaid 画：核心闭环、图片录入、练习；每步有页面/接口 | DONE |
| DS-004 | 8 页线框图 | 霹雳马桶 + 人机 | P0 | DS-002/003 | 登录、首页、录入/编辑（三种题型）、任务中心、列表、详情、练习、统计（P1）；标注组件与状态 | DONE |
| DS-005 | 设计 tokens + 组件清单 | 霹雳马桶 + 人机 | P0 | DS-004 | 颜色/字号/间距/圆角/阴影；按钮/卡片/标签/空错 loading 状态 | DONE |
| DS-006 | 可点击原型 + 可用性测试 | 霹雳马桶 + 人机 | P1 | DS-004/005 | 3 名测试者走核心闭环；问题记录 + 取舍 | DOING |
| DS-007 | 产品设计走查 | 我想抓住风的影子 | P1 | DS-004 | 反馈记录，明确接受/延期/拒绝；不参与开发 | TODO |

> 2026-11-05 状态说明：DS-006 的可点击原型已完成（`docs/product/drafts/prototype.html` + `interaction-map.html`），可用性测试（2–3 人）待做；`docs/product/03-page-specs.md` 的 8 页规范仍需填全。

### 1.2 共同（两人一起）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| SH-001 | API 契约 v0 | 人机 + 霹雳马桶 | P0 | DS-001 | `05-architecture.md` 覆盖 P0 接口、队列/草稿/任务中心、字段、错误码、SSE 事件、图片框题；两人确认 | DOING |
| SH-002 | 仓库骨架 | 人机 + 霹雳马桶 | P0 | 无 | `frontend/`、`backend/`、`contracts/`、`deploy/`、`scripts/`、`.github/`、`.gitignore`、README；`tools/` 本地工具不上传；脚手架/CI 待 FE-001/BE-001 | DOING |
| SH-003 | CI 流水线 | 人机 | P0 | SH-002 | PR 触发 frontend lint/typecheck/build + backend ruff/pytest；绿 | DONE（PR #10；frontend 在 FE-001 后生效） |
| SH-004 | Issue/PR 模板 + 任务板 | 霹雳马桶 | P1 | SH-002 | 模板可用；看板列：Backlog/本周/进行中/评审/完成 | DOING |
| SH-005 | ADR-001/002/003 | 霹雳马桶 | P1 | SH-001 | 技术栈、MVP 范围、识图方案三份 ADR，链接到文档 | DONE |
| SH-006 | M0 验收 + 产品评审同步 | 两人 | P0 | 所有 M0 | 逐项过 `03-roadmap.md` M0 退出检查；下周计划明确 | TODO |
| SH-007 | 风险登记册首次评审 | 两人 | P1 | 无 | `09-risks.md` 每条有负责人/缓解措施/触发信号 | TODO |
| SH-017 | 关闭旧 PRD 任务 | 两人 | P1 | SH-001 | 范围/交互/验收以 01-prd-lite + 02-ia-and-flows + 03-page-specs 为准 | DEFERRED |

> 2026-11-05 状态说明：SH-001 的 v0.3 草案与 `12-backend-alignment.md` 已完成，待两人逐节确认后冻结；SH-004 的 Issue/PR 模板已建，GitHub 看板待建；SH-005 三份 ADR 已建（ADR-002 仍为 Proposed）；SH-017 的旧 PRD 已删除，不再维护独立 PRD。

### 1.3 前端（霹雳马桶）

> 开发页面时参照 `docs/product/drafts/prototype.html` 的结构 + `07-page-drafts.md` / `08-interaction-map.md` 的交互；图片 v2 与旧原型冲突时以 ADR-004 / 05 v0.4 为准。
> 视觉语言以 `04-design-system.md` 第一/第二原则为准：**可读性优先、整体使用流畅**；风格评审先过这两项，再看一致性/美感。
> 2026-11-06：FE-001~012/015 已合入 main；FE-009/019 在 PR #19（CI 绿）；全量 Calm Academic 视觉覆写在 `feat/frontend-calm-redesign` / PR #21（stacked 在 PR #19，CI 绿，未合并）。四核心屏 1366/375、搜索/筛选、创建→分析→生成→任务中心、失败重试均已本地验证。旧 `feat/frontend-style-calm-studio` / PR #20 已关闭。

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| FE-001 | 前端脚手架 | 霹雳马桶 | P0 | SH-002 | Vue3+Vite+TS+Arco+Router+Pinia+ESLint+Prettier；`pnpm dev` 可跑 | DONE（PR #16） |
| FE-002 | 设计 tokens + 基础样式 | 霹雳马桶 | P0 | FE-001/DS-005 | CSS 变量、Arco 主题、字体、reset；与设计稿一致 | DONE（PR #16） |
| FE-003 | 应用壳 + 路由 | 霹雳马桶 | P0 | FE-001 | 路由表；404；未登录占位（原侧边栏壳由 FE-022 替换为 Calm 顶部 appbar + frame） | DONE（PR #16；壳层视觉见 FE-022） |
| FE-004 | API client + 类型 | 霹雳马桶 | P0 | SH-001 | Axios 实例、token 注入、401 处理、错误归一化、类型定义 | DONE（PR #17） |
| FE-005 | 登录/注册页 | 霹雳马桶 | P0 | FE-003/004 | 表单校验、错误提示、loading、跳转 | DONE（PR #17） |
| FE-006 | Mock API | 霹雳马桶 | P0 | SH-001 | P0 接口全部可 mock；前端不依赖后端也能走通页面 | DONE（PR #17） |
| FE-022 | Calm Academic 全量视觉覆写 | 霹雳马桶 | P0 | FE-007/008/009/019 | AppShell + 列表/录入/详情/任务中心/登录/占位/404 按 `calm-academic/index.html` 覆写；1366/375 + 核心路径验证通过 | DONE（PR #21） |
| FE-025 | 首页学习概览 | 霹雳马桶 | P1 | FE-008/009/013/014 | 状态条/KPI/最近错题/薄弱点/关注任务/草稿/快捷入口；stats 失败降级；375/1366 | DONE（PR #34） |

### 1.4 后端（人机）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-001 | 后端脚手架 | 人机 | P0 | SH-002 | FastAPI + 配置 + `/health` + CORS + 日志 + ruff + pytest + uv | DONE（PR #2；follow-up 见 #11） |
| BE-002 | 数据模型 + Alembic | 人机 | P0 | BE-001/SH-001 | users/questions/tags/generated_questions/practice_records/ai_call_logs/draft/generation_task；questions 含 options/blanks/mastery_status；迁移可跑 | DONE（PR #3；follow-up 见 #11） |
| BE-003 | 认证 | 人机 | P0 | BE-002 | 注册/登录/me；JWT；bcrypt；401/409；测试 | DONE（PR #4；follow-up 见 #11） |
| BE-004 | 错题 CRUD + 标签/搜索 | 人机 | P0 | BE-002/003 | 创建/列表/详情/更新/软删；分页筛选搜索；测试 | DONE（PR #7） |
| BE-005 | LLM 客户端 + Prompt + 校验 | 人机 | P0 | BE-001 | DeepSeek `deepseek-flash`（OpenAI 兼容，文本+图像）；三种题型 schema（content_md/options/blanks）；超时/重试；Pydantic 校验；JSON 修复 | DONE（PR #6；题型软约束，ADR-006 再改三段） |
| BE-006 | 分析接口 | 人机 | P0 | BE-004/005 | 返回知识点/题型/难度/错误原因/答案/解析；analysis 可编辑写回；落库；错误码 | DONE（PR #5；answer/explanation 写回 + 标签合并） |
| BE-007 | 生成接口 | 人机 | P0 | BE-006 | content_md/answer_md/explanation_md/题型/options/blanks；校验；失败重试；落库 | DONE（PR #5；一次 3 道的旧形状已由 BE-021/ADR-006 取代） |
| BE-008 | 种子脚本 | 人机 | P1 | BE-004 | `backend/scripts/seed_demo.py`：两个演示账号 `student01`/`student02`（都是 `password123`，第二个用来验用户隔离与越权 403）；每账号 12 道错题（3 道依赖图形/公式）、3 格生成题（`target_index` 1/2/3 + `easy/medium/hard`）、21–24 条练习铺在最近 10 天；**每行入库前先过 `validate_type_payload`**，重复执行不重复插（父题按题干认，不按位置认） | 已完成（#60 已合；两个演示账号、3 格生成题、6 条 quiz 任务、21–24 条练习） |
| BE-009 | API 测试 + OpenAPI | 人机 | P0 | BE-003/004/006/007 | pytest 覆盖核心路径；LLM mock；OpenAPI 可访问 | TODO |

### 1.5 部署/运维（人机主导，林协助）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| OPS-001 | 本地 compose | 人机 | P0 | SH-002 | MySQL 可起；healthcheck；`.env.example`；一条命令启动 | TODO |
| OPS-002 | 部署 spike | 人机 | P0 | SH-002 | 选好服务器/平台；能跑一个 hello world + MySQL；记录步骤 | TODO |
| OPS-003 | 部署脚本/流水线 | 人机 | P1 | OPS-002 | 可重复部署；环境变量注入；回滚步骤 | TODO |
| OPS-004 | 日志与健康检查 | 人机 | P1 | BE-001 | request_id；`/health`；AI 调用日志表 | TODO |

### 1.6 管理端 admin（P1，不进入 11.29 演示）

> 决策：`docs/adr/ADR-005-admin-console.md`。`admin/` 当前仅占位；核心闭环稳定后再开工。

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| ADM-001 | ADR-005 + `admin/README.md` + 文档同步 | 霹雳马桶 | P1 | 无 | ADR Accepted；01/06/README/AGENTS 同步；不写业务代码 | DONE |
| ADM-002 | `users.role` + migration + `require_admin` + seed admin | 人机 | P1 | ADM-001 | student token 403；admin 200；无默认密码 | TODO |
| ADM-003 | `GET /admin/overview` | 人机 | P1 | ADM-002 | 用户/错题/生成题/练习数、AI 成功率、失败任务数与 DB 一致 | TODO |
| ADM-004 | admin app 脚手架 + 登录 + AdminShell | 霹雳马桶 | P1 | ADM-001/002 | 独立 `admin/`；`base=/admin/`；登录/路由守卫；CI build | TODO |
| ADM-005 | 用户列表/搜索/禁用 | 两人 | P1 | ADM-003/004 | 分页、搜索、禁用；不返回 password_hash | TODO |
| ADM-006 | 错题/生成题列表 + 软删除 | 两人 | P1 | ADM-003/004 | 列表/详情/软删；无富文本编辑 | TODO |
| ADM-007 | 任务/AI logs 列表 + 失败重试 | 人机 | P1 | ADM-003/004 | 筛选、重试、错误码/延迟/tokens 可见 | TODO |
| ADM-008 | 审计日志/导出 | 人机 | P2 | ADM-005/006/007 | 删除/重试/禁用留痕；导出脱敏 | TODO |

### 1.7 个人设置 / BYOK（P1，不进入 11.29 演示关键路径）

> 决策：`docs/adr/ADR-007-user-ai-key.md`；Issue #32。Key 只提交后端加密存储，前端不落库、不回显完整值。

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| FE-024 | 个人设置页 + AI API Key UI | 霹雳马桶 | P1 | 无 | `/settings`；账号信息 + AI 设置；masked 回显；密码输入/显示切换；不写 localStorage/Pinia | DONE（PR #35；mock 先行，等 BE-020） |
| BE-020 | 用户 AI Key 设置接口 | 人机 | P1 | FE-024 | `GET/PUT/DELETE /settings/ai`；加密存储；masked；SSRF 白名单；回退系统 Key；测试 | TODO（Issue #32） |

### 1.8 FE-027 收口（2026-11-07）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-025 | 完整三题型编辑 PATCH 扩展 | 人机 | P0 | BE-004 | `QuestionUpdate` 接受 `question_type/options/blanks`；切换题型清掉不适用的一半；四个结构输入任一变动都整题复核 `validate_type_payload`，不合法 400 且回滚；文案走 `structure_problem_zh`；Issue #43 | DONE（#55 已合） |
| BE-026 | 用户生成偏好 + 题型一致性开关 | 人机 | P0 | BE-021 | `users.enforce_same_question_type` 列 + 迁移回填默认 TRUE；`GET/PUT /settings/preferences`；`ai_call_logs.type_policy=strict\|soft`；生成链路按偏好执行硬/软校验；不要在 pipeline 叠二层重试；Issue #44 | PR #58 已补 `generate_v3` + prompt 同题型（176 passed；真实 27/27）；待 rebase 合并；合并前 main 仍软 |
| FE-027 | 题目编辑页（完整三题型） | 霹雳马桶 | P0 | FE-007/FE-020/BE-025 | `/questions/:id/edit`；题干/答案/解析/学科/标签/选项/空位/掌握度；保存后回详情；后端未支持时明确提示 | DONE（PR #51） |
| FE-028 | 设置页题型一致性开关 | 霹雳马桶 | P0 | FE-024/BE-026 | 默认开启；按用户后端持久化；mock/类型/API 就绪；错误可重试 | DONE（PR #51；后端执行等 BE-026） |
| FE-029 | 识图口径收口 | 霹雳马桶 | P0 | FE-016/FE-021/BE-014 | `incomplete` 置灰 + warnings + 编辑后解锁；options/blanks 空值保护；两步 loading + 180s 超时；顶层丢题横幅 | DONE（PR #51） |
| FE-030 | 前端 Vitest 单元测试 | 霹雳马桶 | P0 | FE-001 | 覆盖 API 归一化、错误码、草稿、图片映射、统计、设置；`pnpm test` 可跑并接入 CI | DONE（PR #51；7 files / 20 tests） |
| FE-031 | PRD 清理与文档同步 | 霹雳马桶 | P1 | 无 | 删除 PRD-v0.8 归档；移除 PRD.md 描述；05/04/README 同步 | DONE（PR #51） |

## 2. M1：纵向切片（11.8–11.14）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-010 | SSE 阶段事件（P1） | 人机 | P1 | BE-006/007 | P0 用 `GET /tasks` 轮询；SSE 为 P1；task_status/stage/done/error；断连处理；nginx 配置 | TODO |
| BE-022 | 同组公式结构去重 | 人机 | P1 | BE-021 | 三段并发的遗留：只拒"归一化后逐字相同"，所以两格可能出同一个函数式（实测第 1 格 `2x-a\ln x`、第 3 格同一函数式只多挂一个小问）。做法是抽题干里的 `$...$` 数学式做规范化比较，判"结构相同"后**只给 warnings 提示、不判死**（误判代价是让某张卡变成不可用）。P0 先靠 `too_easy`/`too_hard` 人工反馈兜（16 号 §三） | TODO |
| BE-024 | 识图拆两步（转录 `adaptive` + 结构化 `disabled`） | 人机 | P1 | BE-014 | 本期采用（Issue #47）：转录开思考、结构化关思考；一次 HTTP；`chapter` 只能第 1 跳给；空位统一 `___`；`ai_call_logs` 两行；vision max_tokens ≥16000；超时 ≥180s；前端 loading 已接；验收用概率表述（四张图各 2 次，末题至少 1 次返回 + incomplete） | DOING（后端待实现） |
| BE-023 | ~~密页分块识图~~ **已取消** | 人机 | — | BE-014 | 前提被实测推翻：截断不是"一页题太多"造成的，而是 `reasoning_content` 吃光了 `max_tokens`。关掉思考（`VISION_THINKING=false`）后整页 6 题只要 861 输出 token / 3.9s，余量 89%，不需要分块。留这条记录是为了防止有人按原理由重做。**11-07 补：`thinking.type` 实测还有第三档 `adaptive`（代码里只写了 enabled/disabled），`adaptive` 比 `enabled` 省 35% 时间且照样在正文标 `[不清]`** | 取消 |
| BE-011 | MySQL 兼容性修复 | 人机 | P0 | BE-002 | 迁移在 MySQL 通过；utf8mb4；JSON/datetime/索引检查 | TODO |
| BE-017 | DeepSeek 图片文本提取 spike | 人机 | P0 | BE-005 | 上传单题/多题大学理科题图，`deepseek-flash` 返回 1..N 道题文本（公式 LaTeX）；记录条目完整率、延迟/成本/失败模式；不做 bbox | 已完成（合成图 5 类 + 三张实拍；含图题 `has_figure` 正确且不编造、无题图返回空数组+warning；**实拍 14 条里按"原样过严格入库校验"算是 12/14=86%，这个数触发了 ADR-004 §6 的复审，处置见 §6.1：识图交付文本、结构不自洽就降级**；**延迟/成本的分场景数据在 05 §6.8，不要引用单点**；探针脚本随 PR B 进 `backend/scripts/`） |
| BE-018 | 草稿接口 | 人机 | P0 | BE-003 | `GET/PUT /drafts/me`；每账号 1 份；防抖覆盖；`content` 原样存 draft JSON；`DRAFT_MAX_BYTES=256KB`；测试 | TODO（Issue #46） |
| FE-007 | 录入页（文本） | 霹雳马桶 | P0 | FE-004/006 | 题干/答案/学科/标签；校验；提交；loading/错误 | DONE（PR #18） |
| FE-008 | 列表/详情页 | 霹雳马桶 | P0 | FE-004/006 | 分页、筛选、搜索、详情、空状态、删除确认 | DONE（PR #18） |
| FE-009 | AI 生成 UI | 霹雳马桶 | P0 | FE-007/008/BE-007 | `GET /tasks` 轮询进度、3 张题卡、重试/取消、错误提示 | DONE（PR #19） |
| FE-010 | Markdown + 公式渲染 | 霹雳马桶 | P0 | FE-001 | markdown-it + KaTeX + DOMPurify；长题干/公式/表格测试 | DONE（PR #18） |
| FE-011 | Auth store + 路由守卫 | 霹雳马桶 | P0 | FE-004/005 | token 持久化；401 跳登录；刷新不丢 | DONE（PR #17） |
| FE-012 | 空/错/loading 组件 | 霹雳马桶 | P0 | FE-003 | 统一组件 + 至少 5 处使用 | DONE（PR #18） |
| SH-008 | 契约同步 + 联调 | 两人 | P0 | BE-009/FE-010 | OpenAPI diff；字段/错误码一致；联调记录 | TODO |
| OPS-005 | Staging 部署 | 人机 | P0 | OPS-002/BE-009 | 地址可访问；登录+创建+列表可用；CORS/环境变量正确 | TODO |

## 3. M2：功能完整（11.15–11.21）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-012 | 练习记录 | 人机 | P0 | BE-004 | 创建/查询；时长；对错；防重复；测试 | DONE（PR #9；等 FE-013 真接口联调） |
| BE-013 | 统计接口 | 人机 | P1 | BE-012 | 只实现 `/stats/overview`（trends/weak-points 从 05 删除）；rich shape：total_*、mastery counts、weak_knowledge_points、recent_trend；无记录 accuracy=0 | TODO（Issue #45） |
| BE-014 | 图片文本提取接口（DeepSeek 多模态） | 人机 | P0 | BE-005/BE-017 | 图片校验/压缩；`from-image` 返回 `questions[]`（1..N，公式 LaTeX）；不返回 bbox/candidates；用户确认后每道 `POST /questions`；分析补 answer/explanation；当前阶段不提取附图；错误处理/测试 | DONE（PR #42 已合；`subject/chapter/difficulty` 可空；空结果 200 + `questions[]`；`image_path` 落库并透出列表） |
| BE-015 | 单题重新生成/质量反馈 | 人机 | P0 | BE-007/BE-019 | 「重排该段」已由 `POST /questions/{id}/generate` + `target_index` 覆盖（ADR-006）；剩下是 `/generated-questions/{id}/regenerate` 与质量反馈标记；不覆盖原记录 | TODO |
| BE-016 | 性能/安全加固 | 人机 | P0 | BE-013 | 索引；分页上限；AI 限流；XSS/CORS/文件校验 | TODO |
| BE-019 | 队列 worker + 任务 API | 人机 | P0 | BE-002/BE-005 | `generation_task` worker；queued/running/done/failed；重试 1 次；120s 超时；`GET /tasks`；启动恢复 | DONE（并入 PR #5；并发位与重试窗口由 BE-021 调整） |
| BE-021 | 三段并发生成改造（ADR-006） | 人机 | P0 | BE-006/007/019 | `/generate` 返回 `tasks[]`（整组 3 段 / 单段 `target_index`+`difficulty`）；`generated_questions.target_index` + `generation_task.difficulty` 迁移；按格替换；一段失败不牵连其余；`TASK_MAX_CONCURRENCY=6`；requeue 前判 90s；`generate_v2` prompt；ADR-006 | DONE（PR #39 已合；题型一致性改由 BE-026 用户开关控制） |
| FE-013 | 练习页 | 霹雳马桶 | P0 | FE-008/BE-012 | 逐题、计时、查看答案、自评、结果页 | DONE（PR #23；mock 先行，待联调） |
| FE-014 | 统计/概览页 | 霹雳马桶 | P1 | FE-003/BE-013 | 4 个核心数字 + 图表 + 薄弱点列表 + 空状态 | DONE（PR #24；mock 先行，待 BE-013） |
| FE-015 | 搜索/筛选/标签 | 霹雳马桶 | P0 | FE-008 | URL 同步、防抖、清空、空结果提示 | DONE（PR #18） |
| FE-016 | 图片录入（电脑粘贴/拖入 + 手机相册/拍照）+ 裁剪 + 多题文本提取 | 霹雳马桶 | P0 | FE-007/BE-014 | 电脑粘贴/拖入；手机相册/拍照；上传前裁剪/重置；提取 1..N 道题按 ① ②… 条目展示；逐条编辑/删除/确认；当前阶段只提取文本；失败重试/退回文本；HTTPS 提示 | DONE（PR #29；mock 先行，等 BE-014 联调） |
| FE-017 | 响应式/移动端 | 霹雳马桶 | P1 | FE-013/014 | 375/768/1366 三档；核心三页可用 | DOING（四核心屏 + 练习/统计 + 图片录入已适配 375/1366；768/键盘细节待） |
| FE-018 | 体验/可访问性打磨 | 霹雳马桶 | P1 | FE-013/014 | 对比度、焦点、键盘、文案、loading 不跳动 | DONE（PR #30；草稿双写 + focus/aria/错误聚焦；退出三选项弹窗未做） |
| FE-019 | 任务中心 + 草稿 UI | 霹雳马桶 | P0 | FE-009/BE-018/BE-019 | 录入记录列表、队列/生成状态、失败重试、草稿行/继续编辑；不做复杂筛选/通知 | DONE（PR #19；草稿行已接 GET，保存/恢复归 FE-018） |
| FE-020 | 三种题型编辑器 + 工具栏 | 霹雳马桶 | P0 | FE-007/FE-010 | 选择/填空/解答；选项/空位/答案；LaTeX/编号/表格/插图按时间降级；KaTeX 错误不丢内容 | DONE（PR #25；工具栏增强可后续） |
| FE-021 | 多题识别结果条目 + 选择生成 | 霹雳马桶 | P0 | FE-016/FE-008 | 1..N 条目 ① ②…；逐条编辑/删除/确认；每道显示答案/解析；选中高亮；选择 1–3 道生成；超限提示 | DONE（PR #29；mock 先行） |
| FE-023 | 三段并发生成 UI 适配 | 霹雳马桶 | P0 | BE-006/007（三段）、FE-009/019 | `POST /generate` 返回 `tasks[]`；3 张卡独立状态/难度徽章/单段重试；任务中心折叠「生题 2/3」+ 展开；取消改 P1 | DONE（PR #28；`target_index`/`difficulty` 独立；1–3 段；2026-11-10 已修） |
| SH-009 | 用户走查 + 反馈取舍 | 两人 | P0 | M2 功能 | 3–5 人；问题分级；接受/延期/拒绝有记录 | TODO |
| OPS-006 | MySQL 生产验证 | 人机 | P0 | M1 部署 | 迁移、备份、恢复演练；数据不丢 | TODO |
| OPS-007 | 监控/备份 | 人机 | P1 | OPS-005 | 日志可查；每日备份；磁盘/额度告警 | TODO |

## 4. M3：稳定与答辩（11.22–11.29）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| SH-010 | Bug bash | 两人 | P0 | M2 | P0/P1 清单；修复；回归；无阻塞 bug | TODO |
| SH-011 | 演示种子数据 | 人机/霹雳马桶 | P0 | M2 | 2 个账号；10+ 道大学理科错题（3 道含图）；20+ 练习；数据真实可讲 | TODO |
| SH-012 | 演示脚本 + 彩排 | 两人 | P0 | SH-011 | 3 分钟脚本（图片或文本入口）；连续 3 次成功；分工明确 | TODO |
| SH-013 | PPT | 两人 | P0 | M2 | 7 分钟；10–12 页；每页有讲述要点；两人分段 | TODO |
| SH-014 | 备用视频/截图 | 霹雳马桶 | P0 | SH-012 | 3 分钟录屏；本地+云端；能离线播放 | TODO |
| SH-015 | 最终部署/安全检查 | 人机 | P0 | SH-010 | HTTPS/端口；密钥；CORS；健康检查；回滚 | TODO |
| SH-016 | 最终提交 | 两人 | P0 | 全部 | 仓库、体验地址、PPT、演示账号、README 完整 | TODO |

## 5. 阻塞区

> 有阻塞就写在这里，格式：`[日期] 任务 ID — 阻塞原因 — 需要谁/什么 — 下一步`。

- 暂无。

## 6. 已完成

| 日期 | 任务 | 说明 |
|---|---|---|
| 2026-11-04 | SH-000 | 初始化 `docs/agent/`、`docs/product/`、`docs/adr/`、根级 `AGENTS.md` |
| 2026-11-04 | SH-000b | 输出项目评析、风险登记册、设计流程建议 |
| 2026-11-05 | DS-001 | `01-prd-lite.md` 定稿：大学理科、核心闭环、P0/P1/P2、非目标、指标 |
| 2026-11-05 | DS-002/003/004/005 | `02-ia-and-flows.md`、`07-page-drafts.md`、`04-design-system.md` 完成；`03-page-specs.md` 仍待按 8 页填全 |
| 2026-11-05 | DS-006（部分） | `docs/product/drafts/prototype.html` + `interaction-map.html` 可打开；可用性测试待做 |
| 2026-11-05 | SH-005 | ADR-001/002/003 已建；ADR-002 状态仍为 Proposed，待两人确认 |
| 2026-11-05 | 图片录入 v2 | 正式决策：用户裁剪 + 多题文本提取（①②…）+ 逐条确认 + 选择 1–3 道生成；新增 ADR-004；后端通知 issue #13 |
| 2026-11-05 | BE-001/BE-002/BE-003 | 后端脚手架、9 张表 + 迁移、认证已合并（PR #2/#3/#4） |
| 2026-11-05 | SH-003 | CI #10 已合；frontend job 待 FE-001 后改为真实命令 |
| 2026-11-06 | FE-009/019 | AI 进度轮询、任务中心、失败重试、草稿行完成；PR #19 CI 绿，待合并 |
| 2026-11-06 | FE-022 | Calm Academic 全量视觉覆写：AppShell/四核心屏/登录/占位/404；lint/typecheck/build/format + Playwright 1366/375 通过；PR #21 stacked，待合并 |

## 7. 本周分工建议（11.4–11.7）

| 人 | 主责 | 必须交付 |
|---|---|---|
| 霹雳马桶 | FE-013/014/016/018/020/021/023 已完成（#23/#24/#25/#28/#29/#30）、DS-006 收尾 | FE-017 768/键盘细节；可用性测试记录；03-page-specs 补齐；真接口联调 |
| 人机 | BE-004~BE-007、BE-012、BE-019、OPS-001~OPS-003 | 已合 #6/#5/#9；下一步 ADR-006 三段并发、BE-014 图片、BE-018 草稿、BE-013 统计；#8 docs 收尾 |
| 两人 | SH-001、SH-002、SH-006、SH-007 | API 契约、仓库骨架、M0 验收、风险评审 |
| 我想抓住风的影子 | DS-007 | 设计走查、体验意见、风险同步（不参与开发） |

> 如果 11.7 前只能完成一半：优先保 **API 契约 + 可运行骨架 + 登录/录入/列表的静态页**；高保真原型和完整 PRD 可以延后到 11.8。
