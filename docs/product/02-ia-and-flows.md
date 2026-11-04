# 02 · 信息架构与流程

> 目标：把“产品闭环”翻译成页面、路由、跳转和状态。设计阶段只需覆盖 P0 页面。

## 1. 页面清单

| 页面 | 路由 | 作用 | 主操作 | 优先级 |
|---|---|---|---|---|
| 登录/注册 | `/login` | 进入产品 | 登录/注册 | P0 |
| 首页 | `/` | 去录入/练习/错题本 | 录入错题 | P0 |
| 错题列表 | `/questions` | 找错题、筛选、搜索 | 新建错题 | P0 |
| 录入/编辑 | `/questions/new` | 文本/图片录入 + 显示 + 编辑 + 保存 | 保存 | P0 |
| 任务中心 | `/tasks` | 录入记录、队列状态、失败重试、草稿行 | 继续编辑/重试 | P0 |
| 错题详情 | `/questions/:id` | 看分析、生成题、去练习 | 去练习/重新生成 | P0 |
| 练习 | `/practice/:id?` | 逐题作答、计时、看解析 | 提交答案 | P0 |
| 统计/概览 | `/stats` | 正确率、趋势、薄弱点 | 去练习薄弱点 | P1 |
| 设置 | `/settings` | 账号/退出 | 退出登录 | P1 |

## 2. Sitemap

```mermaid
flowchart TD
  L[登录/注册] --> H[首页]
  H --> Q[错题列表]
  H --> P[练习]
  H --> T[任务中心]
  H --> S[统计/概览 P1]
  Q --> N[录入/编辑]
  N --> T
  Q --> D[错题详情]
  D --> P
  T --> D
  P --> R[练习结果]
  R --> H
  Q --> F[标签/学科筛选]
  S --> W[薄弱知识点]
  W --> Q
```

## 3. 导航

### 桌面

```text
侧边栏                      顶栏
├─ 首页/概览                 ├─ 页面标题/面包屑
├─ 错题本                    ├─ 搜索（列表页）
│   ├─ 全部错题               ├─ 用户菜单/退出
│   └─ 学科/标签
├─ 任务中心
├─ 练习
├─ 统计（P1）
└─ 设置
```

### 移动端

- 底部导航：首页 / 错题 / 练习 / 统计。
- 悬浮按钮：录入错题。
- 侧边栏改为抽屉；筛选改为底部抽屉。

## 4. 流程 A：核心闭环（录入 → 识别/分析 → 编辑 → 保存 → 后台生成 → 练习）

```mermaid
flowchart TD
  A[进入录入/编辑页] --> B{录入方式}
  B -- 文本 --> C[粘贴/拖入题干、答案、选题型]
  B -- 图片 --> IMG[电脑粘贴/拖入；手机相册/拍照]
  IMG --> FRAME[AI 预框核心题目 → 用户确认/切换候选]
  FRAME --> OCR[裁剪 → DeepSeek 识图 → 结构化题目]
  C --> EDIT[显示题目内容 → 编辑]
  OCR --> EDIT
  EDIT --> SAVE{保存}
  SAVE -- 校验失败 --> EDIT
  SAVE -- 成功 --> QUEUE[入库 + 后台整理/生题入队]
  QUEUE --> TASK[任务中心：排队/生成/完成/失败]
  TASK --> DETAIL[错题详情：分析 + 3 道题]
  DETAIL --> PRACTICE[练习：作答/计时/自评]
  PRACTICE --> RECORD[练习记录/错题本]
```

**关键分支**：

- 识图/分析失败：保留输入，可重试；不创建重复错题。
- 生成失败：任务中心显示失败 + 重试；不阻塞连续录入。
- 草稿：服务端 + localStorage 双写；离开/取消有三选项。
- 统计/概览是 P1，不阻塞主闭环。

## 5. 流程 B：练习闭环

```mermaid
flowchart TD
  A[列表/详情] --> B[选择一道生成题]
  B --> C[练习页：题干 + 计时]
  C --> D{用户提交}
  D -- 未作答 --> C
  D -- 已作答 --> E[显示答案/解析]
  E --> F[自评：会/不会]
  F --> G[提交练习记录]
  G --> H{提交成功?}
  H -- 否 --> I[重试/本地暂存]
  I --> G
  H -- 是 --> J[下一题/结果页]
  J --> K[返回首页/统计]
```

**注意**：

- 一次只聚焦一道题；答案/解析默认折叠。
- 计时从进入题卡开始；切后台是否暂停？MVP 不暂停，记录总时长。
- 重复提交：按钮禁用 + 后端幂等/去重。
- 自评“会/不会”作为 `is_correct`；MVP 不做自动判分（除非选择题）。

## 6. 流程 C：薄弱点复习

```mermaid
flowchart TD
  A[首页/统计] --> B[查看薄弱知识点]
  B --> C{有数据?}
  C -- 否 --> D[空状态：先录入/练习]
  C -- 是 --> E[点击知识点]
  E --> F[错题列表：按标签筛选]
  F --> G[选择错题/生成题]
  G --> H[练习]
  H --> I[记录更新]
  I --> B
```

## 7. AI 生成状态机

| 状态 | UI | 用户动作 | 失败/退出 |
|---|---|---|---|
| idle | 空状态 + “开始分析” | 编辑题干 | — |
| detecting | “正在识别题目区域…” + 原图 | 等待/取消 | 重拍/换图/改文本 |
| confirming | 原图高亮框 + “是这道题吗？” + 确认/切换候选 | 确认/切换/取消 | 重拍/换图/改文本 |
| vision | 裁剪后识图进度 | 等待/取消 | 重拍/换图/改文本 |
| submitting | 按钮 loading，表单禁用 | 等待 | 网络错误提示 |
| analyzing | 阶段进度 + 骨架屏 | 等待/取消 | 重试分析 |
| analyzed | 分析卡片 + “生成相似题” | 查看/编辑/生成 | — |
| generating | 3 个题卡骨架 + 阶段文案 | 等待/取消 | 重试生成 |
| validating | “正在校验题目质量…” | 等待 | 自动重试 1 次 |
| partial | 已生成题卡 + 失败提示 | 重试缺失/重新生成 | 重试 |
| success | 3 张完整题卡 | 保存/练习/重新生成 | — |
| error | 错误说明 + 重试 | 重试/返回编辑 | 保留输入 |

**文案模板**：

- 分析中：“正在识别知识点和错误原因，通常需要 5–15 秒。”
- 生成中：“正在生成 3 道同知识点题目，通常需要 10–30 秒。”
- 校验中：“正在检查题目是否可作答、是否依赖图片。”
- 失败：“这次生成没有通过校验，可以重试或换一道题。”

## 8. 页面 ↔ API 映射

| 页面 | 主要 API | 关键数据 |
|---|---|---|
| 登录/注册 | `POST /auth/login`、`POST /auth/register`、`GET /auth/me` | token、user |
| 首页 | `GET /questions?page=1`、`GET /tasks?limit=` | 最近错题、任务状态 |
| 错题列表 | `GET /questions`、`DELETE /questions/{id}` | items、total、filters |
| 录入/编辑（文本） | `POST /questions`、`GET/PUT/DELETE /drafts/me` | question、content_md、options、blanks、analysis |
| 录入/编辑（图片） | `POST /questions/from-image`（先返回候选框，确认后再识别）、`POST /questions` | image_path、candidates、bbox、content_md、analysis |
| 任务中心 | `GET /tasks?question_id=`、`GET /questions/{id}/events`、`POST /tasks/{id}/retry`、`GET/PUT/DELETE /drafts/me` | task status、draft |
| 详情 | `GET /questions/{id}`、`POST /questions/{id}/generate`、`POST /generated-questions/{id}/regenerate` | analysis、generated、tasks |
| 练习 | `GET /questions/{id}/generated`、`POST /practice-records` | 题卡、记录 |
| 统计/概览（P1） | `GET /stats/overview`、`GET /stats/trends`、`GET /stats/weak-points` | 数字、趋势、薄弱点 |

## 9. 流程设计检查

- [ ] 每条流程有起点、终点、主按钮。
- [ ] 每个失败分支有下一步。
- [ ] 每个异步动作有 loading/error/retry。
- [ ] 图片录入有上传/框题/确认/识图/编辑/失败状态；失败可退回文本。
- [ ] 框题确认支持确认/切换候选；P0 不做拖拽画框。
- [ ] 返回/刷新不会丢关键数据（或明确提示）。
- [ ] 重复点击不会产生重复数据。
- [ ] 空数据有引导。
- [ ] 3 分钟内能走完核心闭环。
- [ ] 流程中的页面/API 都能在 `05-architecture.md` 找到。
