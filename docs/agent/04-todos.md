---
owner: 霹雳马桶
last_updated: 2026-11-05
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

> 当前同步（2026-11-05，origin/main @ 2335773）：BE-001/002/003 已合（PR #2/#3/#4）；CI #10 已合；BE-004/005/006/007/BE-012/BE-019 在 open PR；issue #11 跟踪 follow-up。图片录入 v2 已定：用户裁剪 + 多题文本提取 + 条目选择生成。

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
| SH-017 | 合并 PRD v0.9 + 删除 `docs/prd` | 两人 | P0 | SH-001 | PRD/原型/调研归档到 `docs/product/`；按 11.5 决策修订；确认无遗漏后再删远端分支 | DOING |

> 2026-11-05 状态说明：SH-001 的 v0.3 草案与 `12-backend-alignment.md` 已完成，待两人逐节确认后冻结；SH-004 的 Issue/PR 模板已建，GitHub 看板待建；SH-005 三份 ADR 已建（ADR-002 仍为 Proposed）；SH-017 的 PRD v0.8 已归档，PRD v0.9 合并与远端分支删除待做。

### 1.3 前端（霹雳马桶）

> 开发页面时参照 `docs/product/drafts/prototype.html` 的结构 + `07-page-drafts.md` / `08-interaction-map.md` 的交互；图片 v2 与旧原型冲突时以 ADR-004 / 05 v0.4 为准。
> 2026-11-05：FE-001/002/003 已通过 PR #16 合入 main；FE-004/005/006 在 `feat/frontend-fe-004-006` 进行中。

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| FE-001 | 前端脚手架 | 霹雳马桶 | P0 | SH-002 | Vue3+Vite+TS+Arco+Router+Pinia+ESLint+Prettier；`pnpm dev` 可跑 | DONE（PR #16） |
| FE-002 | 设计 tokens + 基础样式 | 霹雳马桶 | P0 | FE-001/DS-005 | CSS 变量、Arco 主题、字体、reset；与设计稿一致 | DONE（PR #16） |
| FE-003 | 应用壳 + 路由 | 霹雳马桶 | P0 | FE-001 | 侧边栏/顶栏/内容区；路由表；404；未登录占位 | DONE（PR #16） |
| FE-004 | API client + 类型 | 霹雳马桶 | P0 | SH-001 | Axios 实例、token 注入、401 处理、错误归一化、类型定义 | DONE（PR #17） |
| FE-005 | 登录/注册页 | 霹雳马桶 | P0 | FE-003/004 | 表单校验、错误提示、loading、跳转 | DONE（PR #17） |
| FE-006 | Mock API | 霹雳马桶 | P0 | SH-001 | P0 接口全部可 mock；前端不依赖后端也能走通页面 | DONE（PR #17） |

### 1.4 后端（人机）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-001 | 后端脚手架 | 人机 | P0 | SH-002 | FastAPI + 配置 + `/health` + CORS + 日志 + ruff + pytest + uv | DONE（PR #2；follow-up 见 #11） |
| BE-002 | 数据模型 + Alembic | 人机 | P0 | BE-001/SH-001 | users/questions/tags/generated_questions/practice_records/ai_call_logs/draft/generation_task；questions 含 options/blanks/mastery_status；迁移可跑 | DONE（PR #3；follow-up 见 #11） |
| BE-003 | 认证 | 人机 | P0 | BE-002 | 注册/登录/me；JWT；bcrypt；401/409；测试 | DONE（PR #4；follow-up 见 #11） |
| BE-004 | 错题 CRUD + 标签/搜索 | 人机 | P0 | BE-002/003 | 创建/列表/详情/更新/软删；分页筛选搜索；测试 | DOING（PR #7 open） |
| BE-005 | LLM 客户端 + Prompt + 校验 | 人机 | P0 | BE-001 | DeepSeek `deepseek-flash`（OpenAI 兼容，文本+图像）；三种题型 schema（content_md/options/blanks）；超时/重试；Pydantic 校验；JSON 修复 | DOING（PR #6 open；base=BE-004） |
| BE-006 | 分析接口 | 人机 | P0 | BE-004/005 | 返回知识点/题型/难度/错误原因/答案/解析；analysis 可编辑写回；落库；错误码 | DOING（PR #5 open） |
| BE-007 | 生成接口 | 人机 | P0 | BE-006 | 恰好 3 题；content_md/answer_md/explanation_md/题型/options/blanks；校验；失败重试；落库 | DOING（PR #5 open） |
| BE-008 | 种子脚本 | 人机 | P1 | BE-004 | 演示账号 + 10 道大学理科错题（3 道含图/公式）+ 20 条练习；可重复执行 | TODO |
| BE-009 | API 测试 + OpenAPI | 人机 | P0 | BE-003/004/006/007 | pytest 覆盖核心路径；LLM mock；OpenAPI 可访问 | TODO |

### 1.5 部署/运维（人机主导，林协助）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| OPS-001 | 本地 compose | 人机 | P0 | SH-002 | MySQL 可起；healthcheck；`.env.example`；一条命令启动 | TODO |
| OPS-002 | 部署 spike | 人机 | P0 | SH-002 | 选好服务器/平台；能跑一个 hello world + MySQL；记录步骤 | TODO |
| OPS-003 | 部署脚本/流水线 | 人机 | P1 | OPS-002 | 可重复部署；环境变量注入；回滚步骤 | TODO |
| OPS-004 | 日志与健康检查 | 人机 | P1 | BE-001 | request_id；`/health`；AI 调用日志表 | TODO |

## 2. M1：纵向切片（11.8–11.14）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-010 | SSE 阶段事件（P1） | 人机 | P1 | BE-006/007 | P0 用 `GET /tasks` 轮询；SSE 为 P1；task_status/stage/done/error；断连处理；nginx 配置 | TODO |
| BE-011 | MySQL 兼容性修复 | 人机 | P0 | BE-002 | 迁移在 MySQL 通过；utf8mb4；JSON/datetime/索引检查 | TODO |
| BE-017 | DeepSeek 图片文本提取 spike | 人机 | P0 | BE-005 | 上传单题/多题大学理科题图，`deepseek-flash` 返回 1..N 道题文本（公式 LaTeX）；记录条目完整率、延迟/成本/失败模式；不做 bbox | TODO |
| BE-018 | 草稿接口 | 人机 | P0 | BE-003 | `GET/PUT /drafts/me`；每账号 1 份；防抖覆盖；测试 | TODO |
| FE-007 | 录入页（文本） | 霹雳马桶 | P0 | FE-004/006 | 题干/答案/学科/标签；校验；提交；loading/错误 | TODO |
| FE-008 | 列表/详情页 | 霹雳马桶 | P0 | FE-004/006 | 分页、筛选、搜索、详情、空状态、删除确认 | TODO |
| FE-009 | AI 生成 UI | 霹雳马桶 | P0 | FE-007/008/BE-007 | `GET /tasks` 轮询进度、3 张题卡、重试/取消、错误提示 | TODO |
| FE-010 | Markdown + 公式渲染 | 霹雳马桶 | P0 | FE-001 | markdown-it + KaTeX + DOMPurify；长题干/公式/表格测试 | TODO |
| FE-011 | Auth store + 路由守卫 | 霹雳马桶 | P0 | FE-004/005 | token 持久化；401 跳登录；刷新不丢 | DONE（PR #17） |
| FE-012 | 空/错/loading 组件 | 霹雳马桶 | P0 | FE-003 | 统一组件 + 至少 5 处使用 | TODO |
| SH-008 | 契约同步 + 联调 | 两人 | P0 | BE-009/FE-010 | OpenAPI diff；字段/错误码一致；联调记录 | TODO |
| OPS-005 | Staging 部署 | 人机 | P0 | OPS-002/BE-009 | 地址可访问；登录+创建+列表可用；CORS/环境变量正确 | TODO |

## 3. M2：功能完整（11.15–11.21）

| ID | 任务 | 负责人 | 优先级 | 依赖 | 验收标准 | 状态 |
|---|---|---|---|---|---|---|
| BE-012 | 练习记录 | 人机 | P0 | BE-004 | 创建/查询；时长；对错；防重复；测试 | DOING（PR #9 open；需 rebase 到 BE-006-007/main） |
| BE-013 | 统计接口 | 人机 | P1 | BE-012 | 总错题/练习/正确率/薄弱知识点/趋势；与数据一致 | TODO |
| BE-014 | 图片文本提取接口（DeepSeek 多模态） | 人机 | P0 | BE-005/BE-017 | 图片校验/压缩；`from-image` 返回 `questions[]`（1..N，公式 LaTeX）；不返回 bbox/candidates；用户逐条确认后每道 `POST /questions`；分析补 answer/explanation；当前阶段不提取附图；错误处理/测试 | TODO |
| BE-015 | 单题重新生成/质量反馈 | 人机 | P0 | BE-007/BE-019 | P0 基础版：单题图标 + 二次确认 + 队列替换；反馈标记；不覆盖原记录 | TODO |
| BE-016 | 性能/安全加固 | 人机 | P0 | BE-013 | 索引；分页上限；AI 限流；XSS/CORS/文件校验 | TODO |
| BE-019 | 队列 worker + 任务 API | 人机 | P0 | BE-002/BE-005 | `generation_task` worker；queued/running/done/failed；重试 1 次；120s 超时；`GET /tasks`；启动恢复 | DOING（并入 PR #5） |
| FE-013 | 练习页 | 霹雳马桶 | P0 | FE-008/BE-012 | 逐题、计时、查看答案、自评、结果页 | TODO |
| FE-014 | 统计/概览页 | 霹雳马桶 | P1 | FE-003/BE-013 | 4 个核心数字 + 图表 + 薄弱点列表 + 空状态 | TODO |
| FE-015 | 搜索/筛选/标签 | 霹雳马桶 | P0 | FE-008 | URL 同步、防抖、清空、空结果提示 | TODO |
| FE-016 | 图片录入（电脑粘贴/拖入 + 手机相册/拍照）+ 裁剪 + 多题文本提取 | 霹雳马桶 | P0 | FE-007/BE-014 | 电脑粘贴/拖入；手机相册/拍照；上传前裁剪/重置；提取 1..N 道题按 ① ②… 条目展示；逐条编辑/删除/确认；当前阶段只提取文本；失败重试/退回文本；HTTPS 提示 | TODO |
| FE-017 | 响应式/移动端 | 霹雳马桶 | P1 | FE-013/014 | 375/768/1366 三档；核心三页可用 | TODO |
| FE-018 | 体验/可访问性打磨 | 霹雳马桶 | P1 | FE-013/014 | 对比度、焦点、键盘、文案、loading 不跳动 | TODO |
| FE-019 | 任务中心 + 草稿 UI | 霹雳马桶 | P0 | FE-009/BE-018/BE-019 | 录入记录列表、队列/生成状态、失败重试、草稿行/继续编辑；不做复杂筛选/通知 | TODO |
| FE-020 | 三种题型编辑器 + 工具栏 | 霹雳马桶 | P0 | FE-007/FE-010 | 选择/填空/解答；选项/空位/答案；LaTeX/编号/表格/插图按时间降级；KaTeX 错误不丢内容 | TODO |
| FE-021 | 多题识别结果条目 + 选择生成 | 霹雳马桶 | P0 | FE-016/FE-008 | 1..N 条目 ① ②…；逐条编辑/删除/确认；每道显示答案/解析；选中高亮；选择 1–3 道生成；超限提示 | TODO |
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

## 7. 本周分工建议（11.4–11.7）

| 人 | 主责 | 必须交付 |
|---|---|---|
| 霹雳马桶 | DS-006 收尾、FE-001~FE-006 | DS-006 可用性测试；前端脚手架、tokens、应用壳、Mock、登录页 |
| 人机 | DS-006 评审、BE-001~BE-009、OPS-001~OPS-003 | 产品设计评审、后端脚手架、数据模型、认证、CRUD、LLM 客户端、部署 spike |
| 两人 | SH-001、SH-002、SH-006、SH-007 | API 契约、仓库骨架、M0 验收、风险评审 |
| 我想抓住风的影子 | DS-007 | 设计走查、体验意见、风险同步（不参与开发） |

> 如果 11.7 前只能完成一半：优先保 **API 契约 + 可运行骨架 + 登录/录入/列表的静态页**；高保真原型和完整 PRD 可以延后到 11.8。
