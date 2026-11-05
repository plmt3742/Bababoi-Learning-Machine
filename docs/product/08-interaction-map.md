# 08 · 页面交互地图与数据流

> owner: 霹雳马桶 · last_updated: 2026-11-05 · read_when: 前端路由、页面联调、交互评审前
> 配套：`07-page-drafts.md`（线框）、`drafts/prototype.html`（可点击的页面原型）、`drafts/interaction-map.html`（可打开的页面地图，点击页面框可打开原型）。
> 说明：本文只描述**页面/状态/数据流**，不含视觉风格。

## 1. 地图总览

```mermaid
flowchart TD
  AUTH[AUTH-01<br/>登录/注册]
  HOME[HOME-01<br/>首页]
  QLIST[QLIST-01<br/>错题列表]
  QEDIT[QEDIT-01<br/>录入/编辑]
  TASK[TASK-01<br/>任务中心]
  QDETAIL[QDETAIL-01<br/>错题详情/生成]
  PRACTICE[PRACTICE-01<br/>练习]
  STATS[STATS-01<br/>统计/概览 P1]
  DRAFT[(草稿存储<br/>localStorage + /drafts/me)]

  AUTH -->|登录成功<br/>JWT + user| HOME
  HOME -->|新建错题| QEDIT
  HOME -->|查看全部| QLIST
  HOME -->|任务入口| TASK
  HOME -->|去练习| PRACTICE
  HOME -.->|P1| STATS
  QLIST -->|新建/编辑| QEDIT
  QLIST -->|打开<br/>question_id| QDETAIL
  QEDIT <-->|草稿 content| DRAFT
  QEDIT -->|保存<br/>question + task_id| TASK
  TASK -->|任务完成<br/>generated_questions| QDETAIL
  TASK -.->|草稿行<br/>继续编辑| QEDIT
  TASK -.->|失败重试| TASK
  QDETAIL -->|去练习<br/>generated_question_ids| PRACTICE
  PRACTICE -->|练习记录<br/>practice_records| HOME
  PRACTICE -->|返回<br/>question_id| QDETAIL
  STATS -.->|薄弱点 tag<br/>P1| QLIST
```

**读图约定**：

- 实线：页面导航。
- 虚线：后台任务/异步状态。
- 点线：草稿/本地存储。
- 粗线（HTML 地图中）：P0 主闭环。
- `P1`：非演示主路径。

## 2. 页面跳转表

| From | 触发 | To | 传递数据 | 优先级 |
|---|---|---|---|---|
| AUTH-01 | 登录/注册成功 | HOME-01 | `access_token`、`user` | P0 |
| AUTH-01 | 已登录访问 | HOME-01 | — | P0 |
| HOME-01 | 点【录入错题】 | QEDIT-01 | 空白编辑器 / 草稿 | P0 |
| HOME-01 | 点【查看全部】 | QLIST-01 | 默认筛选 | P0 |
| HOME-01 | 点任务入口 | TASK-01 | — | P0 |
| HOME-01 | 点【去练习】 | PRACTICE-01 | 可选 `generated_question_id` | P0 |
| HOME-01 | 点统计入口 | STATS-01 | — | P1 |
| QLIST-01 | 点【新建错题】 | QEDIT-01 | 空白编辑器 / 草稿 | P0 |
| QLIST-01 | 点卡片 | QDETAIL-01 | `question_id` | P0 |
| QLIST-01 | 点编辑 | QEDIT-01 | `question_id`、题目内容 | P0 |
| QEDIT-01 | 点【保存】 | TASK-01 / QDETAIL-01 | `question`、`task_id` | P0 |
| QEDIT-01 | 草稿变更 | DRAFT | `content`、`updated_at` | P0 |
| QEDIT-01 | 图片裁剪/提取 | QEDIT-01 | `crop_box`、`image_path`、`questions[]`（1..N） | P0 |
| QEDIT-01 | 确认创建后选择题目 | QEDIT-01 / TASK-01 | `question_ids[]`（≤3）、`task_ids[]` | P0 |
| TASK-01 | 点任务行 | QDETAIL-01 | `question_id`、任务状态 | P0 |
| TASK-01 | 点失败【重试】 | TASK-01 | `task_id` | P0 |
| TASK-01 | 点草稿行【继续编辑】 | QEDIT-01 | `draft.content` | P0 |
| QDETAIL-01 | 点【去练习】 | PRACTICE-01 | `question_id`、`generated_question_ids` | P0 |
| QDETAIL-01 | 点【重新生成】 | QDETAIL-01 | `generated_question_id`、`target_index` | P0 基础版 |
| PRACTICE-01 | 提交练习 | PRACTICE-01 | `practice_records` | P0 |
| PRACTICE-01 | 完成/返回 | HOME-01 / QDETAIL-01 | 练习结果摘要 / `question_id` | P0 |
| STATS-01 | 点薄弱知识点 | QLIST-01 | `tag` 筛选 | P1 |

## 3. 页面级数据流

| 页面 | 数据流入 | 数据流出 | 主要 API | 关键状态 |
|---|---|---|---|---|
| AUTH-01 | `redirect`、空表单 | `access_token`、`user` | `POST /auth/login`、`POST /auth/register`、`GET /auth/me` | idle / submitting / error / success |
| HOME-01 | `user`、最近错题、最近任务 | 入口选择 | `GET /questions?page=1&page_size=3`、`GET /tasks`、`GET /stats/overview`（P1） | loading / empty / partial / error |
| QLIST-01 | URL filters、`page` | `question_id`、删除请求 | `GET /questions`、`DELETE /questions/{id}` | loading / empty / filter-empty / error |
| QEDIT-01 | `draft`、`image`、`question`（编辑）、`questions[]`（提取结果） | `question + task_id`（每道）、`draft`、`task_ids[]` | `GET/PUT/DELETE /drafts/me`、`POST /uploads/images`、`POST /questions/from-image`、`POST /questions`、`POST /questions/{id}/generate` | draft / cropping / uploading / extracting / confirming_items / editing / saving / saved / error |
| TASK-01 | `tasks`、`draft` | `retry`、`question_id`、`draft.content` | `GET /tasks`（P0 轮询）、`POST /tasks/{id}/retry`、`GET /drafts/me` | queued / running / done / failed |
| QDETAIL-01 | `question`、`analysis`、`answer/explanation`、`generated_questions`、`tasks` | `analysis` 更新、`regenerate`、`practice` | `GET /questions/{id}?include=generated`、`PATCH /questions/{id}`、`POST /generated-questions/{id}/regenerate` | loading / analysis pending / generated / partial / error |
| PRACTICE-01 | `generated_questions`、`question_id` | `practice_records` | `GET /questions/{id}?include=generated`、`POST /practice-records` | unanswered / answered / revealed / submit failed / result |
| STATS-01 | `overview`、`weak-points`、`trends` | `tag` 筛选 | `GET /stats/overview`、`GET /stats/weak-points`、`GET /stats/trends` | loading / empty / error |

## 4. 状态机

### 4.1 QEDIT-01

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> editing: 输入/恢复草稿
  editing --> cropping: 选择图片
  cropping --> uploading: 确认裁剪
  cropping --> editing: 取消/重拍
  uploading --> extracting: 上传完成
  extracting --> confirming_items: 返回 1..N 道题（① ②…）
  extracting --> editing: 提取失败/改文本
  confirming_items --> editing: 逐条确认/编辑后进入编辑器
  confirming_items --> cropping: 重拍/换图
  editing --> saving: 点保存（每道题）
  saving --> saved: 入库 + 入队
  saving --> editing: 校验/网络失败
  saved --> analyzing: 分析任务
  analyzing --> analyzed: 答案/解析/知识点
  analyzed --> generating: 勾选 1–3 道 + 生成相似题
  generating --> analyzed: 任务入队/完成
  saving --> error: AI/服务端错误
  error --> editing: 保留草稿
  analyzed --> [*]
```

### 4.2 TASK-01

```mermaid
stateDiagram-v2
  [*] --> queued
  queued --> running: worker 取任务
  running --> done: 整理/生成成功
  running --> failed: 超时/错误
  failed --> queued: 重试
  done --> [*]
```

### 4.3 QDETAIL-01

```mermaid
stateDiagram-v2
  [*] --> loading
  loading --> analysis_pending: 题目已入库、任务未完成
  analysis_pending --> generated: 分析/生题完成
  analysis_pending --> partial: 部分生成
  generated --> generated: 单题重生成
  partial --> generated: 重试缺失
  loading --> error: 加载/权限错误
  generated --> error: 刷新失败
  error --> loading: 重试
```

### 4.4 PRACTICE-01

```mermaid
stateDiagram-v2
  [*] --> unanswered
  unanswered --> answered: 提交答案
  answered --> revealed: 查看答案/解析
  revealed --> result: 自评 + 下一题
  result --> [*]
  answered --> submit_failed: 记录提交失败
  submit_failed --> answered: 重试
```

## 5. 关键数据对象流

| 数据 | 产生 | 传递/存储 | 消费 |
|---|---|---|---|
| `access_token` / `user` | AUTH-01 | auth store；请求头 `Authorization: Bearer` | 所有受保护页面 |
| `draft.content` | QEDIT-01 | localStorage + `PUT /drafts/me`；`GET /drafts/me` 恢复 | QEDIT-01、TASK-01 草稿行 |
| `image file` | QEDIT-01 | 用户裁剪 → 压缩 → 上传；`image_path` | from-image、详情原图 |
| `crop_box`（用户裁剪） | QEDIT-01 上传前 | 归一化 `[x,y,w,h]`；前端裁剪后上传时可为空 | 上传接口、questions |
| `questions[]`（提取结果） | `POST /questions/from-image` | 1..N 道题，`index` 对应 ① ②… | QEDIT-01 条目列表、逐条 `POST /questions` |
| `content_md` / `options` / `blanks` | QEDIT-01 保存 | 每道题 `POST /questions` → `questions` | QDETAIL-01、PRACTICE-01 |
| `question + task_id` | QEDIT-01 保存 | 每道题一个；任务中心查询 | TASK-01、QDETAIL-01 |
| `analysis` / `answer_md` / `explanation_md` | 后台 analysis 任务 | `questions.analysis`/`answer_md`/`explanation_md`；可编辑 | QDETAIL-01、QEDIT 条目 |
| `generated_questions` | 后台 quiz 任务 | `generated_questions`；任务完成 | QDETAIL-01、PRACTICE-01 |
| `practice_records` | PRACTICE-01 | `POST /practice-records` | STATS-01（P1） |
| `stats` | 统计接口 | `GET /stats/*` | HOME-01 / STATS-01（P1） |

## 6. 图片裁剪 + 多题文本提取的数据流（P0）

```text
用户选择图片（电脑粘贴/拖入；手机相册/拍照）
  → 前端裁剪：可选，支持重置原图；裁剪/压缩 ≤5MB / 2000px
  → POST /uploads/images（裁剪后的图片）
  → { image_path, url, width, height }
  → POST /questions/from-image { image_path }
  → { questions: [{index, content_md, question_type, options?, blanks?, has_figure, warnings?}], warnings? }
  → 前端按 ① ② ③ … 展示条目；用户逐条编辑/删除/确认
  → 每道题 POST /questions → { question, task_id }
  → 分析任务返回 answer_md / explanation_md / analysis
  → 用户在条目列表中勾选 1–3 道（高亮）
  → 每个选中题目 POST /questions/{id}/generate → task_id
  → 任务中心/详情查看 3 道相似题
```

**约束**：

- 不做 AI bbox/candidates；服务端不返回框/置信度。
- `crop_box` 只表示用户裁剪（归一化 `[x,y,w,h]`），可选；前端裁剪后上传时可为空。
- 多题共用同一 `image_path`；`index` 从 1 开始，前端显示 ① ② ③ …。
- 当前阶段只提取文字/公式；`has_figure=true` 只提示，不提取附图。
- 多选生成 P0 上限 3 道；超过时提示。

## 7. 地图文件说明

- `drafts/interaction-map.html`：可双击打开的静态页面地图。
- 线型：实线导航、虚线异步任务、点线草稿、粗线 P0 主闭环。
- 每个连线标签都标注“动作 + 数据”。
- 地图下方有页面数据流表和状态机摘要，便于评审时对照。
