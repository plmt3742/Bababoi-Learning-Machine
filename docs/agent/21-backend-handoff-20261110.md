---
owner: 霹雳马桶
last_updated: 2026-11-10
status: active
read_when: 后端开工排期、前后端联调、前端切真实接口、staging/演示准备
---

# 21 · 后端优先开工对接单（2026-11-10）

> 对象：人机（后端）
> 基线：`fix/three-segment-contract` / PR #61；main 的契约修正见 05 / 18 / 20。
> 原则：后端先做“前端要切真实接口”的阻塞项；前端继续用 mock，接口上线就切；不重复实现两套。

## 0. 一句话

后端按“修 #60 种子 → 定 #58 题型开关 → 统计 → 草稿 → OpenAPI → staging → staging 种子”推进；前端每个接口落地就切一个。11.14 staging 可访问，11.29 主流程可演示。

## 1. 后端开工顺序（按这个顺序做）

| 顺序 | 动作 | 为什么先做 | 前置 | 交付/验收 | 前端何时切 |
|---|---|---|---|---|---|
| 1（P0） | 修 PR #60 种子脚本 | 演示数据的第一道门，答案错了比生成慢更难解释 | 无 | 连跑两遍不重复；两处数学答案正确；决定是否补 `generation_task`（演示三段面板就需要 3 条 `status=done` 的 quiz 任务）；顺手修软删过滤、时间排序与「如图」题 | 无需改代码；种子就绪即可演示 |
| 2（P0） | 定 PR #58 题型策略 | strict 与 prompt 不一致，不能带病合并 | 产品确认演示默认（建议：`generate_v3` 落地前关闭 strict） | strict 有测试 + `prompt_version=generate_v3`；或演示默认 off | 设置页已就绪；若演示 off，后端种子把演示账号设为 `false`，前端不动产品默认 |
| 3（P1，按 P0 节奏） | BE-013 统计 overview | 前端统计页与首页一直 mock，是最容易切真接口的一块 | 形状按 §2.1 冻结 | pytest + 空/有数据/软删；用户隔离 | 前端切统计页与首页 |
| 4（P0） | BE-018 草稿 | 任务中心草稿行和录入页双写等真实接口 | 契约按 §2.2 | 204/200/409/256KB；用户隔离 | 前端切草稿双写与任务中心 |
| 5（P0） | BE-009 OpenAPI 导出 | 没有稳定 OpenAPI，前后端只能靠口头对字段 | 统计/草稿/任务/生成路由稳定 | `contracts/openapi/openapi.json`，CI 加 diff 检查 | 作为契约校验；不新增前端类型 |
| 6（P0） | OPS-005 staging | 11.14 硬截止，所有真实联调都依赖它 | 机器/域名/`uploads/` 目标明确；SQLite+WAL 可接受 | HTTPS/HTTP 可访问；`/health`、`/ready` 200；`VITE_USE_MOCK=false` 可构建；CORS；uploads 持久化 | 前端对 staging 构建 |
| 7（P0） | staging 种子 + 演示账号 | 联调和演示需要同一份数据 | staging URL + #60 修完 | `student01/password123`、`student02/password123`；各 12 题；3 道生成题；21-24 条练习；标签齐全；如需三段演示，3 条 done quiz 任务 | 前端走真实走查 |
| 8（P1） | BE-024 两步识图 | 提升识图稳定性，不阻塞主流程 | staging 稳定 | 同一接口/字段；180s；两行 `ai_call_logs` | 前端 loading 已就绪，直接切 |
| 9（P1） | BE-020 BYOK | 用户自带 Key，演示可不依赖系统额度 | staging 稳定 | `/settings/ai` GET/PUT/DELETE；掩码；加密；回退；SSRF | 前端设置页切真实接口 |
| 10（P0，11.29 前） | BE-011 MySQL | 部署目标库，但不阻塞 11.14 | staging 在 SQLite 上跑通 | MySQL 8 上 `alembic upgrade head`；无方言 SQL | 前端无感；切换后回归一轮 |

说明：1-2 是 review 收口，3-7 是 11.14 前必须落地的联调链路（统计在 `04-todos` 里标 P1，但阻塞前端切换），8-10 是后置项。`#58`/`#60` 的完整 review 见 [20](20-three-segment-contract-sync-20261110.md)。

统计的状态以 `04-todos` 为准；这里只排先后。

### 排期建议

| 时间 | 目标 |
|---|---|
| 11.11-11.12 | #60 合并；#58 决策；BE-013 / BE-018 开工 |
| 11.13 | 统计 + 草稿可联调；OpenAPI 导出 |
| 11.14 | staging 可访问；前端 mock off 构建；staging 种子入库 |
| 11.15-11.29 | P1 与 MySQL；前端切完真实接口，压演示流程 |

## 2. 前端需要的后端建设（接口契约）

这一段是前端切接口的依据。字段名照抄，形状不要改；要改先改 05 + OpenAPI，再改前端类型。

### 2.1 统计 overview

`GET /api/v1/stats/overview`

```json
{
  "total_questions": 0,
  "total_generated_questions": 0,
  "total_practice_records": 0,
  "accuracy": 0,
  "mastered_count": 0,
  "reviewing_count": 0,
  "unmastered_count": 0,
  "weak_knowledge_points": [
    {"name": "导数", "wrong_count": 0, "total_count": 0, "accuracy": 0}
  ],
  "recent_trend": [
    {"date": "2026-11-07", "practice_count": 0, "correct_count": 0}
  ],
  "updated_at": "2026-11-07T00:00:00Z"
}
```

规则：

- 只统计当前用户、`deleted_at IS NULL` 的数据；
- `accuracy` 取 0-1，没有练习记录返回 0，不返回 null；
- `weak_knowledge_points` 取 Top 5，只收至少 1 条练习的知识点；
- `recent_trend` 按 Asia/Shanghai 的“天”聚合，无数据返回 `[]`；
- 只实现 `/stats/overview`，不新增 `/stats/trends`、`/stats/weak-points`。

字段口径：

| 字段 | 口径 |
|---|---|
| `total_questions` | 当前用户未软删的错题数 |
| `total_generated_questions` | 未软删的生成题数 |
| `total_practice_records` | 未软删的练习记录数 |
| `mastered_count` / `reviewing_count` / `unmastered_count` | 按父题掌握状态计数，三者之和等于 `total_questions` |
| `weak_knowledge_points` | 父题标签聚合，按错误次数降序取 Top 5 |
| `recent_trend` | 按上海时区切天，只返回有练习的日期 |

前端用：`/stats` 页 4 个数字 + 趋势图 + 薄弱点列表；首页学习概览同源。

### 2.2 草稿

```
GET /api/v1/drafts/me
→ 200 { "content": "<前端 draft JSON>", "version": 3, "updated_at": "2026-11-10T08:00:00Z" }
→ 204 无草稿
```

`PUT /api/v1/drafts/me`

```json
{ "content": "<raw JSON string>", "base_version": 3, "client_updated_at": "2026-11-10T08:00:00Z" }
```

- 成功 200，返回新的 `{content, version, updated_at}`；
- `base_version` 落后返回 409 `DRAFT_VERSION_CONFLICT`；
- `content` 原样存前端 JSON，上限 `DRAFT_MAX_BYTES=256KB`，超限 400 + 中文文案；
- 每账号 1 份，`version` 单调递增；
- `DELETE /api/v1/drafts/me` → 204。

冲突时返回：

```json
{ "detail": { "code": "DRAFT_VERSION_CONFLICT", "message": "草稿已在其他页面更新", "request_id": "..." } }
```

前端要的：版本递增、用户隔离、草稿不含图片 base64。任务中心的草稿行只读 `GET`。

### 2.3 生成偏好（BE-026）

`GET/PUT /api/v1/settings/preferences`

```json
{ "enforce_same_question_type": true, "updated_at": "2026-11-10T00:00:00Z" }
```

- 默认 `true`；PUT 传整个对象；字段用 `StrictBool`，非法值 400 `VALIDATION_ERROR`；
- strict 在 `generate_v3` + “题型必须与原题一致”落地前不算启用；
- 若演示默认关闭 strict，由后端种子把演示账号设为 `false`，前端不改产品默认。

前端用：设置页开关，已就绪。

### 2.4 AI Key（BYOK，P1）

`GET /api/v1/settings/ai` → `{configured, provider, base_url, model, api_key_masked, updated_at}`

```json
{
  "configured": true,
  "provider": "openai_compatible",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-flash",
  "api_key_masked": "sk-****abcd",
  "updated_at": "2026-11-10T00:00:00Z"
}
```

`PUT /api/v1/settings/ai` body `{provider, base_url?, model, api_key}`：

```json
{ "provider": "openai_compatible", "base_url": "https://api.deepseek.com", "model": "deepseek-flash", "api_key": "sk-..." }
```

- 返回同上，`api_key` 至少 8 位；
- `openai_compatible` 的 `base_url` 必须 https + host 白名单；
- 任何响应和日志都不出现原始 Key；
- `DELETE /api/v1/settings/ai` → 204；
- 取 Key 顺序：用户 Key → 系统 `.env` → `AI_PROVIDER_ERROR`；mock 只由 `LLM_MOCK` 决定。

前端用：掩码格式 `sk-****abcd`；进入编辑态清空输入框，不把掩码当 Key 提交。

### 2.5 三段生成与任务（已在 main，不要回退）

`POST /api/v1/questions/{id}/generate`：

- 不带 body：整组 3 个任务；
- body `difficulties`：长度必须 3，允许重复（`easy/easy/hard` 合法）；
- body `target_index` 1-3 + 可选 `difficulty`：只排一段；
- 两种形状不能混传；
- 响应只有 `{"tasks":[{"task_id","target_index","difficulty"}]}`，没有顶层 `task_id`；
- 一组 1-3 个任务，部分 `failed` 是合法返回。

一组只排了 2 段时，就返回 2 个任务：

```json
{
  "tasks": [
    {"task_id": 41, "target_index": 1, "difficulty": "easy"},
    {"task_id": 42, "target_index": 2, "difficulty": "medium"}
  ]
}
```

`GET /api/v1/tasks?question_id=&status=` → `{items:[...]}`，每项含：

```
id, question_id, stage, status, target_index, difficulty, retry_index,
error_code, error_message, created_at, started_at, finished_at
```

`POST /api/v1/tasks/{id}/retry`：只接受 `failed`，返回任务对象。

前端用：任务中心按父题分组、每格取最新一条；1-3 个任务都要正常显示，不假设恒为 3。

### 2.6 图片识图（两步，P1，不改契约）

- 仍是 `POST /api/v1/questions/from-image`，请求/响应字段不变；
- 超时 ≥180s；
- 一次识图写两行 `ai_call_logs`（转录 / 结构化）；
- 结构不自洽时仍按现有降级返回文本 + `incomplete`。

两跳配置：

| 跳 | 输入 | 输出 | 配置 |
|---|---|---|---|
| 1 | 图片 | `chapter` + 题目文本 | `thinking=adaptive`，`prompt_version=vision_text_v1` |
| 2 | 文本 | 现有 `ExtractedQuestion` 形状 | `thinking=disabled`，`prompt_version=vision_structure_v1` |

前端 loading 已是“正在认字 → 正在拆题”，后端上线即可。

### 2.7 通用约定

- 401 未登录；404 不存在/已软删；403 存在但不属于当前用户；
- 例外：`GET /uploads/{user_id}/{filename}` 对非本人/坏文件名/不存在一律 404；
- 错误响应 `{"detail":{"code","message","request_id"}}`；
- 错误码按 05 §6.2 / 18 §8：`AI_TIMEOUT`、`AI_PROVIDER_ERROR`、`AI_RATE_LIMITED`、`AI_INVALID_OUTPUT`、`AI_INVALID_IMAGE`、`AI_INVALID_KEY`、`TASK_NOT_FOUND`、`PRACTICE_DUPLICATE`、`VALIDATION_ERROR`；不新增同义码（如 `TYPE_MISMATCH`）；
- 时间 UTC ISO 8601，字段 snake_case，ID 为整数，列表分页；
- 不改字段名；要改先改 05 + OpenAPI + 前端 `types.ts`；
- 响应/日志不含密钥；浏览器不直接调 LLM；
- 每次 AI 调用写 `ai_call_logs`；quiz 段写 `type_policy=strict|soft`。

## 3. 前端会怎么配合

- 接口没合入 main/staging 前继续用 mock，合入后再切，不提前写死半成品；
- 前端不发明新接口；要加字段先由后端改 05 + OpenAPI，再改前端类型；
- 每次切换后跑 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm build`，并在 staging 做一次真实冒烟；
- 前端同步更新 `04-todos` 和阻塞项，不重复写一套后端逻辑；
- #58：设置页已就绪；strict 还是演示关闭由后端定；演示关闭时后端种子把演示账号设 `false`。

### 切换顺序

| 顺序 | 前端切换 | 依赖 |
|---|---|---|
| 1 | 统计页 / 首页 | BE-013 |
| 2 | 任务中心草稿行 + 录入页草稿 | BE-018 |
| 3 | 设置页 AI Key | BE-020 |
| 4 | 识图 loading（无需改代码） | BE-024 |

## 4. 验收清单

### 后端

- [ ] #60 种子连跑两遍无重复；两处数学答案正确；按需补 3 条 `generation_task`；
- [ ] #58 决策有记录；strict 要么有 prompt + `generate_v3`，要么演示关闭；
- [ ] 统计：空/有数据/软删/用户隔离；
- [ ] 草稿：204/200/409/256KB/用户隔离；
- [ ] OpenAPI 与实际路由一致；
- [ ] staging：`/health`、`/ready` 200；能登录；种子可见；uploads 可写；
- [ ] 以上 P0 完成后才动 P1。

### 前端

- [ ] 统计页/首页切真实接口；
- [ ] 草稿切真实接口；
- [ ] staging 用 `VITE_USE_MOCK=false` 构建；
- [ ] 3 分钟流程：登录 → 录入 → 分析 → 生成 → 单段失败重试 → 练习；
- [ ] 控制台和网络无报错。

### 联调记录

- 每次联调留一行：接口、日期、账号、结果、日志或截图位置；
- 失败先贴错误码和 `request_id`，再贴复现步骤；
- 统计/草稿切换后，空账号和种子账号各走一遍。

## 5. 需要产品/部署确认的三件事

1. #58：演示默认 strict 还是 off？建议 `generate_v3` 落地前 off，落地后再开。
2. #60：演示是否展示三段面板？展示就种 3 条 done 的 quiz 任务；不展示就写进演示脚本。
3. staging 目标：机器/域名/证书/`uploads/` 目录。这三样不定，OPS-005 就动不了。

## 6. 本周完成定义

- staging 可访问，演示账号能登录；
- #60 答案正确，#58 决策有记录；
- 统计 + 草稿真实接口可用，OpenAPI 已导出；
- 前端统计/草稿已切真实接口，并跑通一次端到端；
- 不扩范围；P0 没完成前不做 MySQL、BYOK、两步识图。
