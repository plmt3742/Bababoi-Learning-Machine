---
owner: 霹雳马桶
last_updated: 2026-11-07
status: active
read_when: 后端实现未完成接口、前后端联调、演示前收尾、上云前数据库切换
---

# 18 · 后端未完成接口设计同步（2026-11-07）

> 对象：人机（后端）
> 基线：`origin/main @ 2540f63`（#39 三段并发、#42 图片识图、#49 FE-026、#50 测试控制台、#51 FE-027、#52 状态回写）
> 前端状态：FE-027 已完成并合入 main；真实后端测试环境已起（5173 + 8000，独立 SQLite 测试库，`LLM_MOCK=true`）
> 用途：把前端已实现、当前仍等后端的接口一次性说清；字段名请勿改，若要改先在本文件/Issue 说明。
> 2026-11-07 晚更新：后端已回复，见 §12；BE-025 已在 #55 完成，前端兜底文案已改为真正的错误上报。

## 0. 当前结论

- 前端已完成、等后端的契约：**题型一致性开关、完整三题型编辑、统计 rich shape、草稿、BYOK、两步识图 loading/超时**。
- 核心闭环（登录/文本录入/分析/三段生成/任务中心/练习）和图片上传/识图已在真实后端跑通。
- 当前真实后端仍有两个已知缺口：
  1. 生成题题型仍是 #39 的软约束；默认开启的硬约束要等 BE-026；
  2. `PATCH /questions/{id}` 还不能保存题型结构；要等 BE-025。

## 0.1 数据库策略（已确认）

| 场景 | 数据库 | 说明 |
|---|---|---|
| 当前开发 / 本地 / 测试 | **SQLite** | `backend/.env` 用 `sqlite:///./bababoi.db`；真实联调建议用独立 `bababoi_realtest.db` |
| 云上部署 | **MySQL 8** | 上云前由 **BE-011** 做兼容性验证；不要求现在立刻切 |

约束：

- 现在**不要**为了 MySQL 延误 BE-025/BE-026 等前端阻塞项；SQLite 继续作为开发/测试库。
- 查询、模型、迁移不要写 SQLite 方言；JSON 字段用 SQLAlchemy `JSON`，不要用 SQLite 特有函数。
- 迁移脚本必须同时能在 SQLite 和 MySQL 8 跑通；重点检查 `utf8mb4`、`datetime`、JSON 类型、索引长度、`UPDATE` 子查询限制。
- 11.14 staging 可以先用 SQLite + WAL 解锁“可访问地址”；云上/最终环境切 MySQL 前跑 BE-011，不把切换风险留到 11.29。
- 切换 MySQL 时只改 `DATABASE_URL` 与环境变量，不改业务代码/接口契约。

---

## 1. P0 · BE-026 用户生成偏好 + 题型一致性开关

### 产品决策

- 设置项 `enforce_same_question_type`
- **默认 `true`**
- 按用户后端持久化（换设备/换浏览器一致）
- 开启：生成题题型必须与原题一致；不一致重试 1 次，仍不一致按 `AI_INVALID_OUTPUT` 失败
  - 现有任务级重试已经存在（`retry_index < task_retry_limit=1` + 90s 窗口）；**不要**在 pipeline 再叠一层 `retry_limit=1`，否则最坏 9 次调用/组。
- 关闭：允许换题型，照常入库（当前 #39 的软约束行为）
- 不能只做前端 localStorage；必须后端读取并执行

### API

```http
GET /api/v1/settings/preferences
→ 200
{
  "enforce_same_question_type": true,
  "updated_at": "2026-11-07T00:00:00Z"
}

PUT /api/v1/settings/preferences
body:
{ "enforce_same_question_type": false }
→ 200，返回同上
```

未登录 401；只读写当前用户。

### 数据

给 `users` 加：

```sql
enforce_same_question_type BOOLEAN NOT NULL DEFAULT TRUE
```

或建 `user_settings` 表；迁移必须把历史用户回填为 `TRUE`。

### 生成链路

`POST /questions/{id}/generate` 读取当前用户偏好：

- `true`：`validate_segment` 增加 `original_question_type`；
  - worker 传入原题题型；
  - 不一致重试 1 次，仍不一致 → `AI_INVALID_OUTPUT`；
  - 不新增 `TYPE_MISMATCH`。
- `false`：保持当前 #39 的软约束行为。
- `generate_v2` 的 prompt 保持软措辞；
- **已确认**：加 `ai_call_logs.type_policy`（strict|soft），不升 `prompt_version`；quiz 段写 strict/soft，其它操作为 null。

### 验收

- [ ] 默认 `TRUE`；
- [ ] 关闭后不同题型可入库；
- [ ] 开启后不同题型触发重试并最终失败；
- [ ] 用户隔离；
- [ ] 偏好缺失/非法值回退 `TRUE`；
- [ ] pytest 全绿；
- [ ] 05 §6.9/§7.2、04-todos 同步。

### 前端现状

设置页开关、mock、类型、ADR-008 已完成并合入 main（#51）。真实执行只差本 Issue（#44）。

---

## 2. P0 · BE-025 完整三题型编辑 PATCH 扩展（已完成 #55）

> 后端 #55 已实现并合并；`chapter` 本来就在可改清单里。前端比对失败此时视为后端 bug，不再提示“未支持”。

### 背景

前端 `/questions/:id/edit` 已支持完整三题型编辑；现有 PATCH 只允许题干/答案/解析/学科/标签/analysis/mastery_status，不能保存题型结构。

### 需要改

`QuestionUpdate` 增加：

- `question_type: Literal["choice","blank","solve"] | None`
- `options: list[ChoiceOption] | None`
- `blanks: list[BlankAnswer] | None`

`question_service.update`：

- 应用这些字段；
- 任一变化（`question_type` / `content_md` / `options` / `blanks`）后调用 `validate_type_payload`；
- 校验失败 400 `VALIDATION_ERROR`，message 用中文可读文案；
- 题型切换时清理不适用字段：
  - 切到 `solve`：`options=null`、`blanks=null`
  - 切到 `choice`：`blanks=null`
  - 切到 `blank`：`options=null`
- 未提交字段保持原值（`exclude_unset` 语义）。

### 验收

- [ ] choice→blank、blank→solve、solve→choice；
- [ ] 非法选项/空位数≠答案数 → 400 不落库；
- [ ] 只改题干不影响题型结构；
- [ ] `GET /questions/{id}` 返回新结构；
- [ ] pytest 全绿；
- [ ] 05 §6.4 PATCH 字段表同步。

### 前端现状

前端会比对 PATCH 返回的 `question_type/options/blanks`；后端未支持时明确提示“后端尚未支持题型结构编辑（BE-025）”，不会静默丢改动。
当前仓库已有 `feat/be-025-question-type-edit` 分支，可直接在此分支实现。

---

## 3. P0 · BE-018 草稿接口

```http
GET /api/v1/drafts/me
- 有草稿：200 { content, version, updated_at }
- 无草稿：204

PUT /api/v1/drafts/me
body: { content, base_version, client_updated_at }
- 每账号 1 份；防抖覆盖；
- 成功返回新 { content, version, updated_at }
- base_version 落后 → 409 DRAFT_VERSION_CONFLICT

DELETE /api/v1/drafts/me → 204
```

**已确认**：`content` 原样存前端 draft JSON，不拆字段；新增 `DRAFT_MAX_BYTES`，建议 **256KB**（前端接受；草稿不含图片 base64），超限 400 + 中文文案。

验收：

- [ ] 空草稿 204；
- [ ] 创建/覆盖/版本递增；
- [ ] 旧 `base_version` 409；
- [ ] 用户隔离；
- [ ] pytest 全绿；
- [ ] 05 §6.5b 同步。

---

## 4. P1 · BE-013 统计接口

`GET /api/v1/stats/overview`：

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
    { "name": "导数", "wrong_count": 0, "total_count": 0, "accuracy": 0 }
  ],
  "recent_trend": [
    { "date": "2026-11-07", "practice_count": 0, "correct_count": 0 }
  ],
  "updated_at": "2026-11-07T00:00:00Z"
}
```

规则：

- 只统计当前用户、未软删数据；
- `accuracy` 为 0–1；无练习记录返回 **0**（不是 null）；前端类型已收紧为 `number`；
- `weak_knowledge_points` 按练习记录聚合到父题标签，Top 5；无数据返回 `[]`；
- `recent_trend` 按天聚合；无数据返回 `[]`；
- 不造数、不返回假趋势；
- 用户隔离。

验收：

- [ ] 与数据库一致；
- [ ] 无记录 `accuracy=0`、数组为空；
- [ ] 三类掌握状态之和 = `total_questions`；
- [ ] pytest 覆盖空/有/软删；
- [ ] 05 §6.6 改为 rich shape。

前端 FE-014 已按此形状完成，后端实现后可直接切真实接口。

---

## 5. P1 · BE-020 BYOK（Issue #32）

```http
GET /api/v1/settings/ai
→ { configured, provider, base_url, model, api_key_masked, updated_at }

PUT /api/v1/settings/ai
body { provider, base_url?, model, api_key }
→ 同上；api_key ≥8

DELETE /api/v1/settings/ai → 204
```

要求：

- 原始 Key 永不返回；加密存储；
- `openai_compatible` 的 `base_url` 必须 https + host 白名单（防 SSRF）；
- 取 Key 顺序：用户配置 → 系统 `.env` → **AI_PROVIDER_ERROR**；mock 只由 `LLM_MOCK` 决定，不再静默回退 mock；
- 失败用明确错误码，建议补 `AI_INVALID_KEY`；
- `ai_call_logs` 记录 `key_source=user|system`，不记录 Key；
- pytest 覆盖加密/掩码/删除/回退/非法 Key。

前端 FE-024 已完成，等真实接口。

---

## 6. P1 · BE-024 两步识图（本期采用）

目标：转录 + 结构化拆成两步，一次 HTTP，前端契约不变。

- 第 1 跳：图 → `{ chapter, questions:[{index, content_md}] }`
  - `thinking=adaptive`
  - `max_tokens ≥16000`
  - `prompt_version=vision_text_v1`
  - `chapter` 只能第 1 跳给
- 第 2 跳：纯文本 → 现有 `ExtractedQuestion` 形状
  - `thinking=disabled`
  - `prompt_version=vision_structure_v1`
  - 空位统一改写成 `___`
- `ai_call_logs` 一次识图写两行；
- `RECOGNIZE_CLIENT_TIMEOUT_S` 90 → **≥180s**；前端已按 180s 实现；
- 保留一步模式作为配置回退（`VISION_TWO_STEP` 或等价开关）；
- 结构不自洽仍按 v0.6.3 降级成文本 + `incomplete`；
- 验收：四张真图各跑 2 次，被页边裁掉的末题至少 1 次返回且带 `incomplete=true`；墙钟 17–60s；日志两行；一步可回退；pytest 全绿。

前端 loading 已做「正在认字 → 正在拆题」，后端未上线前一步识图也能正常结束。

---

## 7. 演示前交付 · BE-008 / BE-009 / OPS-005

### BE-008 种子

- 可重复执行，不重复插数据；
- 演示账号 `student01 / password123`；
- 10+ 道大学理科错题（3 道含图/公式）；
- 20+ 条练习；
- 3 条 `generated_questions`（带 `target_index` / `difficulty`）；
- 不跑真实 LLM。

### BE-009 OpenAPI

- 导出 `contracts/openapi/openapi.json`；
- 覆盖当前实际路由（含 `tasks` / `images`）；
- CI 加 diff 检查（至少 warn）。

### OPS-005 staging

- 可访问地址（HTTPS 优先）；
- **先用 SQLite + WAL 解锁 11.14**；云上再切 MySQL 8；
- 前端用 `VITE_USE_MOCK=false` 构建；
- `/health`、`/ready` 200；
- CORS、环境变量、`uploads/` 持久化；
- 回滚步骤。

验收：新环境 seed 后 `student01` 能登录；种子数据可见；OpenAPI 与路由一致；staging 可走通核心闭环。

---

## 8. 跨接口约定

- 时间统一 ISO 8601 UTC；
- 所有资源按当前用户隔离；
- 404：不存在/已软删；403：存在但不属于当前用户；
  - **例外：图片取图 `GET /uploads/{user_id}/{filename}` 对“非本人/坏文件名/不存在”一律 404，不给 403**（避免泄露文件是否存在）；
- 错误码沿用 05 §6.2：
  `AI_TIMEOUT` / `AI_PROVIDER_ERROR` / `AI_RATE_LIMITED` / `AI_INVALID_OUTPUT` / `AI_INVALID_IMAGE` / `AI_INVALID_KEY` / `TASK_NOT_FOUND` / `PRACTICE_DUPLICATE` / `VALIDATION_ERROR`；
- 不新增同义错误码（如 `TYPE_MISMATCH`）；
- 每个接口补 pytest；测试不调真实 LLM；
- 改字段/路径必须同步 05 + 04 + 前端 `types.ts`。

---

## 9. 建议实现顺序

1. **BE-025 + BE-026**（前端功能已就绪，阻塞真实联调）
2. **BE-018**（草稿，任务中心/录入页）
3. **BE-013**（统计）
4. **BE-020**（BYOK）
5. **BE-024**（两步识图）
6. **BE-008 / BE-009 / OPS-005** 并行推进（11.14 staging 硬截止）

---

## 10. 需要后端确认

后端已在 §12 回复 1–5；当前只剩 **staging 部署目标**未定：

- 机器 / 域名 / HTTPS 证书归属 / `uploads/` 挂载目录。
- 后端方案：11.14 staging 用 SQLite+WAL；CI 加一条 MySQL `alembic upgrade head` 冒烟；MySQL 不进 11.14 路径。

---

## 11. 前端当前测试环境

- 前端：`http://127.0.0.1:5173`，`VITE_USE_MOCK=false`（`frontend/.env.local`，已 gitignore）
- 后端：`http://127.0.0.1:8000`，独立测试库 `backend/bababoi_realtest.db`，当前已用临时 Key 切到 `LLM_MOCK=false`
- 测试账号：`realtest01 / password123`
- 已验证：文本分析 → 三段生成 3 题（题型全部 solve）→ 练习；图片上传 → `from-image` 真实返回 2 条 → 图片错题入库
- 真实 DeepSeek 的 Key 只注入后端进程环境，未写入前端、未提交仓库；后端重启后需重新注入或写 `backend/.env`
- 统计/草稿/BYOK/题型开关接口当前会 404/读取失败，属于预期

## 12. 后端回复确认（2026-11-07）

| 问题 | 后端结论 |
|---|---|
| BE-025 | **已完成 #55**；`chapter` 本来就在可改清单；切换题型清掉不适用的一半；不合法 400 且整笔回滚；前端兜底文案改为错误上报 |
| BE-026 偏好存哪 | **users 加列**（本期只有一项布尔；第二项偏好出现时再抽 `user_settings`） |
| 硬模式日志 | 加 `ai_call_logs.type_policy`（strict/soft），**不升 `prompt_version`**；现有任务级重试已经存在，**不要**在 pipeline 再叠一层 |
| BE-024 两步识图 | **本期就做两步**：第 1 跳 adaptive、第 2 跳 disabled；vision `max_tokens` 8000→≥16000；`RECOGNIZE_CLIENT_TIMEOUT_S` 90→≥180；保留 `VISION_TWO_STEP` 一步回退 |
| BE-024 验收 | “密页 4 题不丢末题”改为概率性：四张真图各跑 2 次，被裁末题至少 1 次返回且带 `incomplete=true` |
| BE-013 | **只实现 `/stats/overview`**；`/stats/trends`、`/stats/weak-points` 从 05 删除；前端用 `overview.recent_trend` / `overview.weak_knowledge_points` |
| BE-018 | `content` 原样存前端 draft JSON；新增 `DRAFT_MAX_BYTES`，建议 **256KB**（前端接受；草稿不含图片 base64） |
| BE-020 Key 回退 | 用户 Key → 系统 `.env` → **AI_PROVIDER_ERROR**；不再静默回退 mock；mock 只由 `LLM_MOCK` 决定 |
| 图片鉴权 | 取图非本人/坏文件名/不存在 **一律 404**，不给 403；§8 通用 403 规则有例外 |
| accuracy | 后端返回 **0**；前端类型已收紧为 `number` |
| BE-008 seed | 必须与 BE-013 联动：按未软删统计，三类掌握状态之和 = 总数，每条题带知识点标签 |
| staging | **SQLite+WAL**；MySQL 不进 11.14 路径；CI 加 MySQL `alembic upgrade head` 冒烟；只剩部署目标待定 |
| 合并节奏 | 6 个任务里 5 个改 05，**串行合**（合一个、下一个 rebase） |
