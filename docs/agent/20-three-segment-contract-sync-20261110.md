---
owner: 霹雳马桶
last_updated: 2026-11-10
status: active
read_when: 三段并发契约、target_index/difficulty、PR #58/#60 回馈、演示种子
---

# 20 · 三段并发契约同步与 PR #58/#60 回馈（2026-11-10）

> 对象：人机（后端）/ 两位开发
> 基线：`fix/three-segment-contract`（从 main 切出）；本文只同步文档，同分支的前端代码修正见 §2；不动 `Resource/`
> 用途：把后端实际契约、我们这边的修正、PR #58 / PR #60 的 review 结论一次写清，避免再按旧印象写接口或做演示。

## 0. 一句话结论

`POST /questions/{id}/generate` 只返回 `tasks[]`；`target_index` 是格位、`difficulty` 独立，任务数可为 1–3，前端不得假设恒为 3。PR #58 的 strict 必须补 `generate_v3` + 明确的同题型提示词才能合并；PR #60 的种子脚本有两处数学答案错误，且缺 `generation_task`，三段面板演示不了。

## 1. 后端契约事实

| 事实 | 内容 |
|---|---|
| 响应形状 | 只有 `{"tasks":[{"task_id","target_index","difficulty"}]}`；**没有顶层 `task_id`**，后端从未双发 |
| 整组 | 一次排 3 个 `generation_task`（`target_index` 1/2/3，难度默认 `easy/medium/hard`）；整组 `difficulties` 长度必须为 3 |
| 难度重复 | 整组 `difficulties` 允许重复值（例如 `easy/easy/hard` 合法），后端不按重复判错 |
| 单段 | 传 `target_index`（1–3）+ 可选 `difficulty`；不传难度时按该格默认值 |
| 独立关系 | `target_index` 只是格位，`difficulty` 独立；`target_index=3` + `easy` 合法，反之亦然 |
| 任务数 | 一组可为 1–3 个任务；前端按 `tasks.length` 渲染，不得假设恒为 3 |
| 部分失败 | 一等状态：某段 `failed` 不牵连其余两段；单段重试走 `POST /tasks/{id}/retry` |
| 并发 | `TASK_MAX_CONCURRENCY=6`；`question_id + stage + target_index` 唯一，3 段不会互相顶掉 |
| 重排 | 整组重生成入队即软删旧组；单段只替换自己那一格，旧题 `practice_records` 保留 |

补充三条口径：

1. **格位不是难度**：不要再用“第 1 段=简单、第 3 段=困难”的隐式映射；难度以请求里的 `difficulty` 为准，落库时也按请求档位改写。
2. **1–3 段是常态**：任务中心与详情页要能处理只排了 1 段或 2 段的情况（重试、单段重排都会产生）。
3. **部分成功不是错误**：`tasks[]` 里混有 `failed` 是合法返回；UI 显示实际成功数，不要整组判失败。

## 2. 我们这边修了什么（前端，2026-11-10）

- `GenerateQuestionsPayload` 增加 `target_index`，请求类型与后端字段对齐。
- mock 语义修正：`target_index` 当格位、`difficulty` 独立；`target_index=3 + easy` 在 mock 里也合法，不再把难度当格位。
- `summarizeSegments` 支持 1–3 个任务；任务中心「生题 N/M」按实际任务数 M 显示，不再写死 3。
- 删掉旧顶层 `task_id` 的兜底分支，只认 `tasks[].task_id`。
- `QuestionDetailView` 的分段面板判据不变（`detail.tasks.some(isSegmentTask)`），所以种子数据必须有 `generation_task` 才会走三段 UI（见 §3）。

回归方式：`summarizeSegments` 用 1/2/3 个任务各跑一次；删兜底后跑一次详情页和任务中心，确认没有残留的顶层 `task_id` 读取。

这些是前端内部修正，不改对外响应形状；文档层面只需要记住 §1 的契约事实。

## 3. 后端 PR #60 review（BE-008 演示种子脚本）

在一次性 SQLite 库上把分支脚本连跑两遍，结果如下。

| 项 | 结果 |
|---|---|
| 幂等 | 通过；两次执行后 2 users / 24 questions / 6 generated / 45 practice / 0 `generation_task` |
| BLOCKING 数学 1 | 生成题 `2x^3-6x+1` 答案写成「x=0 极大值 1，x=1 极小值 -1」。正确答案：**x=-1 极大值 5，x=1 极小值 -3**（`f'(x)=6x^2-6`） |
| BLOCKING 数学 2 | 正态分布单选题的 C「X²+Y² ~ χ²(2)」和 D「X/Y ~ t(1)」**都正确**（两个独立标准正态之比是 Cauchy，即 t(1)）；单选题出现两个正确选项 |
| 演示缺口 | 只插 3 条 `generated_questions`、0 条 `generation_task`；前端分段面板靠 `tasks.some(isSegmentTask)` 才出现，种子打开的是旧进度面板，任务中心也没有「生题 3/3」组 |
| Minor（软删） | 父题查询与生成行的 `exists` 检查未过滤 `deleted_at`；`gen_rows` 会把软删行算进去 |
| Minor（排序） | 局部重跑时 `created_at` 用 `len(new_questions)`，新题可能排到父题之前 |
| Minor（图片） | 三角形题写「如图」但 `image_path` 为 NULL；答案给的是方法不是数值，演示时答不出来 |

处置建议：

1. 两处数学错误必须修，演示题答案错误比“生成慢”更难解释。
2. 种子补 3 条 `generation_task`（`stage=quiz`、`target_index` 1/2/3、`status=done`），让详情页和任务中心都能展示三段过程；如要演示失败重试，可留一条 `failed`。
3. 「如图」题要么配图，要么换成纯文本可作答题；当前阶段生成题也要求纯文本可作答。
4. 顺手修 `deleted_at` 过滤与 `created_at` 排序，避免重复执行后数据错位。

复现要点：脚本指向一次性库（不要用 `backend/bababoi.db`）；跑第二遍确认行数不增长，再核对答案和 `generation_task` 计数。两处答案错误用求导/分布定义直接验算即可，不依赖模型。

## 4. 后端 PR #58 更新（BE-026 题型一致性）：generate_v3 已落地

2026-11-10 更新：后端已按 review 补上 `generate_v3`。strict prompt 明写「题型必须与原题一致」，版本按策略分叉（strict=`generate_v3`，soft=`generate_v2`），`ai_call_logs` 与 `generated_questions` 都跟策略走；9 张 mock 卡按题型 × 难度，队列测试不再关开关。本地复跑 **176 passed**；真实 strict 复测 **27/27 题型一致、27/27 校验通过**，默认维持开启。

### 4.1 仍成立的历史判断

- `generate_v2` 的软 prompt 不能配 strict；这条是当时的阻塞，现已被 #58 修复。
- 7 个红色队列测试是 mock 故意混题型，真实链路 3/3 solve、ADR-006 27/27；mock 失败率不是产品失败率。
- 27/27 的独立复测支持默认 strict。

### 4.2 合并前

- PR #58 需要 rebase 到最新 main，解决 05 §6.9/§7.3/变更记录与 #61/#62 的文档重叠。
- 当前 main 仍是 `generate_v2` 软约束，strict 在 #58 合并后才生效。
- 演示不再需要默认关闭 strict；如果 #58 合并延后，才用关闭开关兜底。

### 4.3 前端

- 设置页已就绪；#58 合并后真实链路按 strict 执行。
- 前端 mock 的 101-104 与 fallback 本来就是同题型、三段内容不同，不需要照搬后端 9 张卡；难度内容不随卡位变只是展示差异。

## 5. 文档/代码同步清单

| 位置 | 改动 |
|---|---|
| `05-architecture.md` §6.4 | 补「整组=3 段 / 单段 target_index + 可选 difficulty / 格位与难度独立 / 1–3 任务 / 响应只有 tasks」 |
| `05-architecture.md` §7.3 | `generate_v2` = 软约束；strict 必须 `generate_v3` + 同题型提示词；main 仍是软 |
| `05-architecture.md` §14 | 新增 v0.6.8 变更行 |
| `18-backend-unfinished-api-sync-20261107.md` | §1 生成链路 + §12「硬模式日志」更正；顶部加 2026-11-10 补充 |
| `docs/adr/ADR-008-...` | 追加「strict 落地前置」，不改原决策 |
| `04-todos.md` | FE-023 / BE-026 / BE-008 状态补记 |
| `19-project-stage-report-20261107.md` | 两处表述更正（最多 3 道 / 软约束 3/3） |
| `product/01-prd-lite.md` | P0 生成行附近补「3 道为目标、单段失败可重试」 |
| `docs/README.md` | agent 索引 + 变更记录 |
| 前端（本分支，不在纯文档范围） | payload `target_index`、mock 语义、`summarizeSegments` 1–3、删旧 `task_id` 兜底 |

## 6. 未决 / 下一步

1. **BE-026**：补 `generate_v3` + 「题型必须与原题一致」；PR #58 改后再合。未落地前 strict 不启用。
2. **BE-008**：修两处数学错误；种子补 3 条 `generation_task`；「如图」题配图或换题；顺手修 `deleted_at` 过滤与 `created_at` 排序。
3. **演示口径**：三段面板要能展示 1–3 段（含单段失败重试）；「3 道」是目标，不是硬承诺。
4. **验收数字标注来源**：mock / 真实调用 / ADR 记录要分开写，避免再次把 mock 失败率当成产品失败率。
5. **文档维护**：后续若 strict 真正启用，先改 05 §6.9/§7.3 与 ADR-008，再改代码；不要只在聊天里说“已经用 strict 了”。
