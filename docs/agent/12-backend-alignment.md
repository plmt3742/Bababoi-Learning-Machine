---
owner: 霹雳马桶
last_updated: 2026-11-05
status: active
read_when: 后端对接、M0 契约确认、分支合并/删除前
---

# 12 · 后端对接结果（对齐单 v2 回复）

> 对象：人机（后端）
> 基线：`chore/init-repo-structure` + 2026-11-05 决策
> 结论：**PRD v0.8 已归档为参考，不原样作为契约；`docs/prd` 可以删除，后续从归档修订 PRD v0.9，以 `chore/init-repo-structure` 为开发基准。**

## 0. 一句话结论

- 核心闭环：**录入 → 识别/分析 → 显示/编辑 → 保存 → 后台整理/生成 → 练习 → 记录/统计/错题本**；练习 P0，统计/概览 P1。
- 队列、草稿、结构化题型、单题重新生成：**按 P0 保留**，05 补表/端点。
- 题型/编辑器：**三种题型 + 工具栏 P0 增强**；表格/复杂编号可按时间降级。
- 录入：电脑粘贴/拖入；手机相册/拍照；两端都 **AI 预框 + 用户确认**。
- 裁剪：**保留裁剪步骤 P0；P0 可确认/切换候选，并可移动/缩放 AI 框**；从零画框 P1。AI 判定整页 → 整页识别不框；无 candidate → 整图识别。
- OCR：**不使用独立 OCR**；FR-11 砍出 11.29 路径。
- 复习模式：**11.7 前不做，列 P1**。
- Python：**统一 3.13**，不是 3.12。
- 产品决策：**霹雳马桶 + 人机共同拍板**；我想抓住风的影子只评审，不参与开发。
- 分支：`docs/prd` 的 PRD/调研已归档，原型图已完成参考、后续将独立设计；**可以删除**，建议先打 tag 保留历史。

## 1. 基线更正

| 项 | 旧说法（对齐单 v2） | 实际基线 |
|---|---|---|
| 开发人员 | 前端、后端、产品经理三方 | **霹雳马桶 + 人机两人开发**；我想抓住风的影子只评审 |
| 产品设计 | 产品经理负责，开发执行 | **两位开发共同负责产品设计** |
| Python | 3.12 | **3.13**；保留 3.13 venv，用 `uv` + `uv.lock` |
| 真名 | 文档使用真名 | **真名只留本地/私聊**；仓库统一昵称/handle |
| CI | AGENTS 写 3.12，CI 已有 | **CI 尚未创建**；第一个 PR 补 3.13 版 `ci.yml` |
| 裁剪 | 前端手动框选 P0 | **AI 预框 + 确认 + 移动/缩放 P0；从零画框 P1** |
| 模型 Key | 要求前端提供 | **后续由霹雳马桶提供**；后端先用 mock + provider 抽象 |

## 2. 逐条决策

| # | 事项 | 决策 | 类型 |
|---|---|---|---|
| 1 | Python 版本 | 统一 3.13；不要重建 3.12 venv | ✅ 已定 |
| 2 | 后台队列 | 按 PRD P0 保留；`generation_task` + worker + SSE | ✅ 已定 |
| 3 | 服务端草稿 | 按 PRD P0 保留；`draft` + `GET/PUT /drafts/me` | ✅ 已定 |
| 4 | 结构化题型 | 按 PRD P0；`options`/`blanks` JSON；`question_type` 枚举 | ✅ 已定 |
| 5 | 裁剪/框题 | 裁剪步骤 P0；AI 预框 + 确认/切换 + 移动/缩放 AI 框；从零画框 P1 | ✅ 已定 |
| 6 | 图片限制 | 前端选图 ≤20MB；压到 ≤5MB/2000px；上传 ≤10MB；服务端再压到 ≤5MB/2000px；支持 JPEG/PNG/WebP | ✅ 已定 |
| 7 | 单题重新生成 | P0 基础版：卡片图标 + 二次确认 + 队列替换；不做批量/复杂动画；M2 紧张可降 P1 | ✅ 已定 |
| 8 | 掌握状态 | 加 `mastery_status` 枚举列，默认 `unmastered` | ✅ 已定 |
| 9 | 密码规则 | 采纳 ≥8 位 + 登录限流；回填 PRD | ✅ 已定 |
| 10 | `users.email` | P0 注册页不显示；DB 保留 nullable，API 可选 | ✅ 已定 |
| 11 | 模型/grounding | 需 Key 实测；不支持则框题降级整图识图 | ❓ 待测试 |
| 12 | PRD 治理 | PRD 管范围/交互/验收；05 管 API/数据/技术 | ✅ 已定 |
| 13 | 真名 | 仓库只用昵称/handle | ✅ 已定 |
| 14 | CI | 第一个 PR 补 `ci.yml`；3.13；`LLM_MOCK=true` | ✅ 已定 |
| 15 | OpenAPI | 后端先导出 `contracts/openapi/openapi.json`；前端 FE-004 生成类型 | ✅ 已定 |
| 16 | `backend/` 冲突 | 先合结构/文档/CI，后端再 rebase 本地代码 | ✅ 已定 |
| 17 | 核心闭环 | 录入 → 识别/分析 → 显示/编辑 → 保存 → 后台整理/生成 → 练习 → 记录/统计/错题本；练习 P0，统计/概览 P1 | ✅ 已定 |
| 18 | 题型/编辑器 | 三种题型 + 工具栏 P0 增强；表格/复杂编号可按时间降级 | ✅ 已定 |
| 19 | 录入入口 | 电脑粘贴/拖入；手机相册/拍照；两端都 AI 预框 + 确认 | ✅ 已定 |
| 20 | 任务中心 | P0 只做列表 + 状态 + 失败重试 + 草稿行；不做复杂筛选/通知 | ✅ 已定 |
| 21 | OCR | 不使用独立 OCR；FR-11 砍出 11.29 路径 | ✅ 已定 |
| 22 | 复习模式 | 11.7 前不做；列 P1 | ✅ 已定 |
| 23 | 草稿双写 | 服务端 + localStorage 双写；防抖 5s；三选项退出；见 `06-draft-dual-write.md` | ✅ 已定 |
| 24 | 数据/API 口径 | 05 v0.3 统一：`content_md`/`answer_md`/`explanation_md`/`options`/`blanks`/`mastery_status`；tags 多对多 | ✅ 已定 |

## 3. 后台队列：采用方案

### 3.1 数据表

```text
generation_task
- id
- question_id
- user_id
- stage: analysis | quiz
- status: queued | running | done | failed
- retry_index
- error_code / error_message
- created_at / started_at / finished_at
```

### 3.2 执行流程

```text
保存错题
  → questions 写入
  → generation_task(analysis, queued) 写入（同一事务）
  → 立即返回 question + task_id

worker
  → 取 queued（FIFO）
  → 置 running
  → 调 LLM 整理
  → 写 analysis + tags
  → 入队 quiz 任务
  → 置 done

失败
  → retry_index + 1，重试 1 次
  → 仍失败置 failed
  → 任务中心显示【重试】
```

### 3.3 约束

- 不引入 Redis/Celery。
- 单 worker 或 API 1 worker + 1 个后台 worker；并发 2。
- 启动时把 `running` 重置为 `queued`，避免重启卡死。
- 调 LLM 时不持有 DB 事务；结果落库单独事务。
- 同一 `question_id + stage` 只允许一个 active task，防重复入队。
- 单任务硬超时 120s。

### 3.4 SSE 与轮询

```text
GET /api/v1/questions/{id}/events
event: task_status
data: {"stage":"analysis","status":"running"}

event: task_status
data: {"stage":"quiz","status":"done","generated":3}

event: error
data: {"code":"AI_TIMEOUT","message":"..."}
```

- SSE 用 `fetch` + `ReadableStream`，不用 `EventSource`（需要 Authorization/POST）。
- 心跳 15s；断线由前端轮询 `GET /questions/{id}` 或 `GET /tasks?question_id=` 兜底。
- SSE 是进度通道，不是队列替代。

## 4. 裁剪/框题：P0 方案

```text
电脑粘贴 / 拖入：
原图 → AI 检测核心题目 → 返回 candidates（bbox + confidence）
→ 前端高亮“是这道题吗？”→ 用户确认/切换候选 + 移动/缩放 AI 框
→ 服务端按最终 crop_box 裁剪 → DeepSeek 识图 → 可编辑题干 → 分析

手机相册 / 拍照：
原图 → AI 检测核心题目 → 返回 candidates
→ 前端高亮“是这道题吗？”→ 用户确认/切换候选 + 移动/缩放 AI 框
→ 服务端按最终 crop_box 裁剪 → DeepSeek 识图 → 可编辑题干 → 分析

整页 / 无候选：
AI 判定整页 → 整页识别，不框；无 candidate / grounding 不可用 → 整图识别
```

两端都走 AI 预框 + 确认；P0 可移动/缩放 AI 框，从零画框 P1。粘贴截图如果 AI 判断是单题高置信，可把“确认”做成一次点击快捷确认，但仍然保留确认入口。

- P0：确认/切换候选 + **移动/缩放 AI 框** + 重置为整图；**从零画框 P1**。
- AI 判定整页 → 整页识别，不框。
- 无 candidate / grounding 不可用 → 整图识别；此时没有框可调。
- 框题失败 → 整图识图；识图失败 → 文本录入。
- 后端需支持：

```json
{
  "candidates": [
    {
      "index": 1,
      "bbox": [0.12, 0.18, 0.76, 0.42],
      "confidence": 0.92,
      "preview_url": "/api/v1/uploads/1/xxx_crop.jpg"
    }
  ],
  "selected_index": 1
}
```

- `bbox` 用归一化 `[x,y,w,h]`（0–1），基于去 EXIF/旋转后的图片。
- 服务端裁剪；前端只展示高亮框。

## 5. 图片限制

最终口径（已定）：

| 环节 | 规则 |
|---|---|
| 前端选择 | JPEG/PNG/WebP；原图 ≤20MB（手机常见 12–20MB） |
| 前端压缩 | 最长边 2000px，目标 ≤5MB |
| 上传接口 | ≤10MB（兜底） |
| 服务端 | Pillow 校验真实格式、纠正旋转、去 EXIF、再压到 ≤5MB/2000px |
| 存储 | 存压缩后的图；详情页展示压缩图 |

PRD v0.8 的“jpg/png ≤10MB”需要同步改成上表；05 v0.3 按此更新。

## 6. 模型 Key 与框选测试

### 6.1 Key

- 后续由霹雳马桶提供，走 `.env` 或密码管理器，**不进仓库/群聊**。
- 后端先做 provider 抽象 + mock；测试用 `LLM_MOCK=true`。
- CI 不调用真实 LLM。

### 6.2 后端测试清单

测试集：10 张左右。

- 4 张单题：打印体、公式、表格、图形
- 2 张多题图：验证核心题目选择
- 1 张旋转图
- 1 张模糊/低质量图
- 1 张无题目/空白图
- 1 张手写题

验收：

- 单题图 top-1 框包含核心题目 ≥ 80%
- 多题图 top-1 是用户最可能录入的题；否则可切换
- 无题目图返回 `candidates: []` + `warnings`，不崩溃
- 记录延迟、图片 token 成本、失败模式

降级：

- 若 grounding 不支持：P0 退回整图识图 + 用户编辑；框题降 P1。
- 不阻塞文本录入闭环。

## 7. PRD 与治理

### 7.1 结论

- **PRD 有必要**：v0.8 的草稿、队列、任务中心、题型、编辑器、验收标准是 PRD-lite 没有的。
- **不能照搬**：团队、Python、目标用户、裁剪、图片限制、密码等需要修订。
- **最终形态**：`docs/product/PRD.md` v0.9，由霹雳马桶 + 人机共同维护；`01-prd-lite.md` 只做速览。
- **技术契约**：`docs/agent/05-architecture.md` 管 API/数据/技术。

### 7.2 事实来源优先级

```text
1. 代码 + OpenAPI
2. 05-architecture（API / 数据 / 技术）
3. PRD（范围 / 交互 / 验收）
4. 01-project / 02-goals（摘要 / 目标）
5. 03-roadmap / 04-todos
6. 其他文档
7. Resource/ docx
```

冲突规则：范围/交互/验收 → PRD；API/数据/技术 → 05；跨域变更两边同时升版本。

## 7.1 数据/API 口径 v0.3（2026-11-05 定稿）

> 本节覆盖 05 v0.2 的字段命名；05 正文 v0.3 按此更新。

### 7.1.1 表与字段

```text
questions
- id, user_id, subject, chapter
- content_md          # 题干，Markdown + LaTeX
- answer_md           # 原题答案，可选
- explanation_md      # 原题解析，可选
- question_type       # choice | blank | solve
- options             # JSON: [{label, content_md}]
- blanks              # JSON: [{index, answer_md}]
- analysis            # JSON: {topic_type, difficulty, knowledge_points, error_reasons, solution_summary}
- mastery_status      # unmastered | reviewing | mastered，默认 unmastered
- status              # confirmed（MVP 固定；删除用 deleted_at）
- image_path, crop_box, crop_image_path, detection_confidence
- created_at, updated_at, deleted_at

tags / question_tags  # 多对多；analysis.knowledge_points 同步到 tags
draft                  # user_id UNIQUE, content_json, version, updated_at
generation_task        # 见 3.1
generated_questions    # content_md, answer_md, explanation_md, question_type, options, blanks, difficulty, model, prompt_version, validation_status, validation_score
practice_records       # user_id, generated_question_id, user_answer, is_correct, duration_seconds
ai_call_logs           # 见 5.2；增加 queue_wait_ms
```

### 7.1.2 关键 API

```text
POST /api/v1/questions
  {content_md, answer_md?, subject, question_type, options?, blanks?, tags?, source_type?, image_path?}
  → 保存 + 自动入队 analysis；返回 {question, task_id}

PATCH /api/v1/questions/{id}
  {content_md?, answer_md?, subject?, tags?, analysis?}   # analysis 可编辑写回

POST /api/v1/questions/{id}/analyze     # 重新分析，入队
POST /api/v1/questions/{id}/generate    # 入队 quiz
GET  /api/v1/questions/{id}/events      # SSE 任务进度
GET  /api/v1/tasks?question_id=         # 轮询兜底
POST /api/v1/tasks/{id}/retry

POST /api/v1/questions/from-image       # 两阶段：candidates → candidate_index + crop_box? 识图
GET/PUT/DELETE /api/v1/drafts/me

POST /api/v1/generated-questions/{id}/regenerate   # P0 基础版
POST /api/v1/practice-records
GET  /api/v1/stats/overview                        # P1
GET  /api/v1/tags
```

### 7.1.3 命名决策

- 题目正文统一用 `content_md`，不再用 `original_text`；列表返回 `excerpt`。
- 生成题答案/解析统一用 `answer_md` / `explanation_md`。
- 标签用 `tags` + `question_tags` 多对多；`chapter` 保留为可选字符串。
- `status` MVP 固定 `confirmed`；删除用 `deleted_at`；不作复杂状态机。
- `mastery_status` 由练习/复习更新；P0 筛选默认 `unmastered`。

### 7.1.4 单题重新生成（P0 基础版）

- 生成题卡片右上角图标 → 二次确认「是否重新生成第 n 题？」。
- 确认后创建 `generation_task(stage=quiz, target_index=n)`；完成后替换该题，其余两道不动。
- 不做批量/复杂动画；M2 紧张时降 P1，并在 `04-todos.md` 标注。

## 8. 分支决策：`docs/prd`

### 8.1 分支内容

`docs/prd` 分支包含：

- `docs/PRD.md`（v0.8，详细产品契约）→ 已归档为 `docs/product/PRD-v0.8-reference.md`
- `docs/原型图/`（10 张 PNG）→ 已完成参考，后续将独立设计，不归档
- `docs/开源项目调研.md` → 已归档为 `docs/product/开源项目调研.md`
- 根 `README.md` → 仅一句项目名，无保留价值

### 8.2 与当前基线的明显冲突

| 冲突 | `docs/prd` | 当前决策 |
|---|---|---|
| 核心闭环 | 录入→生成→录入记录/错题本；练习 P1、统计 P2 | 录入→识别/分析→编辑→保存→后台生成→练习→记录/统计/错题本；练习 P0、统计 P1 |
| 目标用户 | 不限学段 | 大学理科优先，通用后续 |
| Python | 3.12 | 3.13 |
| 录入 | 电脑粘贴为主；移动端不专项优化 | 电脑粘贴/拖入；手机相册/拍照；两端 AI 预框 |
| 裁剪 | 手动框选 P0 | AI 预框 + 确认/调整 P0；从零画框 P1 |
| 图片 | jpg/png ≤10MB | WebP + 前端压缩 + 服务端 10MB/5MB |
| 密码 | ≥6 位 | ≥8 位 + 限流 |
| 产品角色 | 产品经理负责 | 两位开发共同负责产品设计 |
| 单题重生成 | P0 | P0 基础版 |
| 队列/草稿/题型/掌握状态 | P0 | P0（05 已补） |
| OCR | FR-11 P1 | 不使用独立 OCR，砍出 11.29 路径 |
| 复习模式 | P1 | P1（11.7 前不做） |

### 8.3 结论

**可以删除 `docs/prd`。** 内容已处理：

1. PRD v0.8 → 已归档 `docs/product/PRD-v0.8-reference.md`（标注“参考，不构成契约”）。
2. 开源项目调研 → 已归档 `docs/product/开源项目调研.md`。
3. 10 张原型图 → 已完成参考，后续将独立设计，不归档。
4. 根 README → 仅一句项目名，无保留价值。

建议保留 git 历史（可选，但推荐）：

```bash
git tag archive/docs-prd-v0.8 origin/docs/prd
git push origin archive/docs-prd-v0.8
git push origin --delete docs/prd
```

> 删除分支不会删除已归档文件；只是删掉远端的 `docs/prd` 引用。若不需要 PRD 的提交历史，可跳过 tag，直接删除分支。

## 9. 行动项

### 9.0 脚手架分工（明确）

- **前端（霹雳马桶）**：FE-001 前端脚手架（Vue3 + Vite + TS + Arco + Router + Pinia + ESLint/Prettier）。
- **后端（人机）**：BE-001 后端脚手架（Python 3.13 + FastAPI + `/health` + CORS + 日志 + ruff + pytest + uv + `.env.example`）。
- **共同**：第一个 PR 补 `.github/workflows/ci.yml`；后端导出 `contracts/openapi/openapi.json`；前端 FE-004 生成类型。

### 后端（人机）

- [ ] BE-001：完成 FastAPI 脚手架（3.13 + `/health` + CORS + 日志 + ruff + pytest + uv）；与 FE-001 对齐 `/health`、错误信封、OpenAPI。
- [ ] 把 venv 固定到 3.13，`uv.lock` 提交。
- [ ] 按 05 v0.3 实现 `generation_task`、`draft`、`options/blanks`、`mastery_status`、`content_md` 等字段。
- [ ] 实现队列 worker + SSE 进度 + 轮询兜底。
- [ ] 实现 `GET/PUT /drafts/me`。
- [ ] 实现 `POST /questions/from-image` 两阶段框题。
- [ ] 三种题型的结构化识别/生成 schema（`content_md`/`options`/`blanks`）。
- [ ] 单题重新生成 P0 基础版。
- [ ] 用 Key 做识图/grounding spike；先 mock。
- [ ] 第一个 PR 补 `ci.yml`（3.13、`LLM_MOCK=true`）。
- [ ] 导出 `contracts/openapi/openapi.json`。
- [ ] 本地 `backend/` rebase 到 `chore/init-repo-structure`，不要另起一套。

### 前端（霹雳马桶）

- [ ] PRD v0.9 合并/修订。
- [ ] 原型/调研归档到 `docs/product/`。
- [ ] 页面规范补 `detecting/confirming`、任务中心、草稿、三种题型。
- [ ] 图片输入：电脑粘贴/拖入 + 手机相册/拍照；两端 AI 预框 + 确认/切换 + 移动/缩放 AI 框；从零画框 P1。
- [ ] 三种题型编辑器 + 工具栏（P0 增强）。
- [ ] 练习 P0；统计/概览 P1。
- [ ] 任务中心/草稿 UI。
- [ ] FE-004 从 OpenAPI 生成类型。

### 共同

- [ ] 11.7 前逐节确认 05 v0.3。
- [ ] 11.8 冻结 API v1（只加不改）。
- [ ] 确认 `docs/prd` 删除时间。

## 10. 未决问题

| ID | 问题 | 负责人 | 截止 |
|---|---|---|---|
| O-01 | 框题 grounding 是否可用 | 人机 | Key 到位后 1 天 |
| O-02 | `docs/prd` 合并 PR 与删除时间 | 两人 | 11.7 前 |

## 11. 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-11-05 | 初版：对齐单 v2 回复、队列方案、分支决策 | 霹雳马桶 |
| 2026-11-05 | 追加：练习 P0、统计 P1、三种题型+工具栏、录入入口、任务中心、草稿双写、无 OCR、单题重生成、图片限制、05 v0.3 口径 | 霹雳马桶 |
| 2026-11-05 | 按《框题口径-最终》调整：P0 可移动/缩放 AI 框；从零画框 P1；from-image 支持 `crop_box`；补 BE-001 脚手架分工 | 霹雳马桶 |
