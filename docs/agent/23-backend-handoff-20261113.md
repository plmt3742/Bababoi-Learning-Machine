---
owner: 霹雳马桶
last_updated: 2026-11-13
status: active
read_when: 后端继续开发、部署前对齐、前后端联调复核
---

# 23 · 后端对接单（2026-11-13）

> 对象：人机（后端）
> 基线：`main @ d0fc52b`（#58 / #62 / #63 / #64 / #65 已合；前端 PR #68 / #69 已合）
> 一句话：**前端已经全部用真接口验过，当前没有阻塞项。** 后端只剩 BYOK 一个接口、识图两步入 staging 的确认，以及部署本身（11.14 硬截止）。

## 0. 已合并、不用再处理

| 内容 | 结果 |
|---|---|
| #58 生成偏好 + strict 题型 | 已合 `06e29e7`；`generate_v3`、`preference_updated_at`、requeue 测试都在 |
| #65 OpenAPI 快照 + CI 防漂移 | 已合 `4bebb28`；快照覆盖 auth/questions/images/tasks/practice/drafts/stats/settings |
| 前端联调收口 | 已合 `2acadef`；时间解析、统计 mock 对齐、404 降级、Ctrl/⌘+Enter |
| 文档收口 | 已合 `d0fc52b`；FE-032 标 DONE |

CI 在 PR 与 main 上都是绿的；本地 `export_openapi.py --check` 与 pytest 均通过（见 §7）。

## 1. 前端已实测通过的接口（不用重复确认）

用真实本地后端 + `seed_demo.py` 种子数据跑过，结论如下：

| 接口 | 实测结果 |
|---|---|
| `POST /auth/login`、`GET /auth/me` | 200；`created_at` 为 UTC naive |
| `GET /questions`、`GET /questions/{id}?include=generated` | 200；列表/详情/生成题字段齐全 |
| `GET/PUT/DELETE /drafts/me` | 204 → 200(v1) → 旧版本 409 `DRAFT_VERSION_CONFLICT` → 204 → 204 |
| `GET /stats/overview` | 200；accuracy 0.667、`recent_trend` 7 条（稀疏） |
| `GET /practice-records`、`GET /tasks` | 200；24 条练习、3 条任务 |
| `POST /uploads/images` | 201，返回 `{image_path, url, width, height}` |
| `POST /questions/from-image` | 200，4 条 `questions[]`（mock 模型） |
| `GET /uploads/{user_id}/{filename}` | 200 `image/jpeg` |
| `GET /settings/preferences` | 默认 `true`；PUT 关闭后重新登录仍为关闭，且 `updated_at` 不因登录变化；传 `"yes"` → 400 `VALIDATION_ERROR`；未登录 401 |

页面层也验过：设置页“最近更新”把 UTC `08:38` 显示为本地 `16:38`；开关关闭 → 刷新 → 仍关闭 → 再打开；375 / 768 / 1366 三档截图无溢出。

## 2. 请保持不变的契约（前端依赖）

### 2.1 时间格式（最容易出事的一条）

后端目前是两套口径：

- `drafts`、`stats` 在路由层补了时区：`2026-11-13T08:38:18Z`；
- `questions`、`tasks`、`practice-records`、`auth.me`、`settings.preferences` 是 UTC naive：`2026-11-13T08:38:18`（无后缀）。

前端已在 `frontend/src/utils/time.ts` 统一按 UTC 解析，两套都能正确显示。**演示前请不要只改一半**：

- 全部保持现状：不需要任何动作；
- 若要统一补 `Z`：五个 naive 端点一起改，同时更新 05 §6、OpenAPI 快照和前端测试；
- 只改其中几个：会出现“有的页面对、有的差 8 小时”，比不改更难排查。

另外 `settings.preferences.updated_at` 用独立时间戳（`preference_updated_at`）是对的，不要退回 `users.updated_at`——登录会刷新后者。

### 2.2 错误信封与错误码

- 形状固定：`{"detail": {"code", "message", "request_id"}}`。
- 运行时参数校验是 **400 `VALIDATION_ERROR`**；OpenAPI 快照里的 422 是 FastAPI 生成器行为，前端只按 200 schema 取类型。
- 前端已映射的错误码：`AI_TIMEOUT`、`AI_PROVIDER_ERROR`、`AI_RATE_LIMITED`、`AI_INVALID_OUTPUT`、`AI_INVALID_IMAGE`、`AI_INVALID_KEY`、`TASK_NOT_FOUND`、`VALIDATION_ERROR`、`INTERNAL_ERROR`。新增码请提前说一声，否则页面只能显示“任务失败（CODE）”。

### 2.3 逐接口要点

**草稿**

- `content` 必须是 JSON 对象（前端整包编辑器状态），后端原样存取；超过 256KB → 400 中文文案。
- 409 不回传服务端草稿（前端自己会再 GET 一次）；删除后再存，`version` 从 1 重新计。
- `client_updated_at` 收下但不参与判断——只能认 `version`。

**统计**

- `accuracy` 是 0–1，没有练习返回 `0` 而不是 `null`；`mastered + reviewing + unmastered = total_questions`。
- `recent_trend` 按 Asia/Shanghai 切天、**只返回有练习的日期**；前端按稀疏渲染。若改成补 7 天零值，请先通知，前端 mock 与图例要一起改。
- 生成题计数排除父题已软删的行。

**生成**

- 响应只有 `tasks[]`，1–3 段；没有顶层 `task_id`、没有取消接口。
- `target_index` 是格位、`difficulty` 独立（`index=3 + easy` 合法）。
- 单段失败不牵连其余两段。

**图片**

- 上传 201 的 `url` 需要 JWT 才能取（前端目前只把图片当识图输入、不在页面回显；将来回显会用带 Authorization 的 blob 请求，请保持鉴权，不要改成公开静态目录）。
- `from-image` 空结果是 `200 + questions: []`，不是错误；`incomplete` 的唯一判据是“条目带 warnings”；结构不自洽整条降级为 `solve` 纯文本。
- `chapter` 只由第一跳（转录）提供（PR #67）；请求带 `subject` 时逐条覆写。
- 超时 180s：前端 `extractQuestions` 已经设 `timeout: 180_000`，后端 `RECOGNIZE_CLIENT_TIMEOUT_S` 保持 ≥180。

**偏好**

- `GET/PUT /settings/preferences` 整份覆盖；请求体是 `StrictBool`，非法值 400。
- 前端 404 时降级为“后端未启用”，所以旧环境不会崩，但演示环境请确保已迁移到 `c8e1b6a4d902`。

## 3. 唯一还需要写的接口：BYOK（BE-020）

前端已按 `05 §6.9` + ADR-007 做好页面与类型，接口 404 时自动降级。若要实现，请按下面形状，不要另起字段：

```text
GET    /api/v1/settings/ai
→ 200 {configured, provider, base_url, model, api_key_masked, updated_at}
→ 404 未实现（前端显示“后端未启用”）

PUT    /api/v1/settings/ai
← {provider: "deepseek" | "openai_compatible", base_url?, model, api_key}
→ 200 同上；api_key ≥8 位

DELETE /api/v1/settings/ai
→ 204（回退系统 Key）
```

- 原始 Key 永不返回；只返回掩码。
- `openai_compatible` 的 `base_url` 必须 https + host 白名单（防 SSRF）。
- 取 Key 顺序：用户配置 → 系统 `.env` → `AI_PROVIDER_ERROR`；`ai_call_logs.key_source` 记 `user|system`。
- 用户 Key 失效/额度不足返回明确错误（前端已映射 `AI_INVALID_KEY`），不要静默回退系统 Key。

## 4. 识图两步（PR #67）的对接点

对外仍是同一个端点、同一组字段，前端不需要改代码。合并/部署后请确认：

1. staging 实拍一张多题图：末题至少返回一次、残缺条目 `incomplete=true`；
2. 等待上限 180s 与前端一致；
3. 一次识图写两行 `ai_call_logs`（按跳），前端不读这张表，只用于排查。

## 5. 演示数据的一个小问题（建议演示前处理）

种子脚本的 3 道生成题题型统一是 `solve`，而父题里有 `choice`/`blank`，且 strict 默认开启。新生成的题不受影响（strict 在生成时生效），但演示账号里已有的 3 张卡看起来会“原题是选择题，相似题是解答题”。

三选一，建议前两个：

1. 种子按父题 `question_type` 派生生成题题型（改 `seed_demo.py`，重新 `--reset`）；
2. staging 灌完种子后，对演示用的 1–2 道题现场重新生成一次；
3. 接受现状（不影响功能，只是观感）。

## 6. 部署（11.14 硬截止）—— 前端需要的确认

| 项 | 要求 |
|---|---|
| 访问地址 | 11.14 前有一个别人能打开的 URL；手机拍照必须 **HTTPS** |
| 前端产物 | `cd frontend && pnpm build` → `dist/`（本地实测 4s 内完成）；nginx 静态托管 + `/api/v1` 反代 |
| 路由回退 | SPA 需要 `try_files $uri $uri/ /index.html` |
| CORS | `CORS_ORIGINS` 加上前端域名（含端口）；drafts 已需要 `PUT`，main 的 allow_methods 已包含 |
| 上传目录 | `uploads/` 挂持久卷；`GET /uploads/...` 保持 JWT 鉴权 |
| 环境变量 | `JWT_SECRET`、`DEEPSEEK_API_KEY`（或 `LLM_MOCK=true`）、`DEMO_PASSWORD`、`CORS_ORIGINS`、`UPLOAD_DIR`；BYOK 另需 `SETTINGS_ENCRYPTION_KEY` |
| 部署后 | `alembic upgrade head` + `scripts/seed_demo.py`（口令用 `DEMO_PASSWORD`） |
| 健康检查 | `/health`、`/ready` 均 200 |
| 数据库 | 时间紧就 SQLite + WAL（1 worker）；BE-011 MySQL 兼容未做，别在最后一天切 |
| 回滚 | 记录上一个镜像/提交 + 数据备份位置 |

## 7. 后端自查命令（与前端联调前跑一遍）

```bash
cd backend
uv run ruff check app tests
uv run pytest                                   # 期望全绿（含 197+ 用例）
uv run python scripts/export_openapi.py --check # 期望 “OpenAPI 快照一致”
uv run alembic upgrade head
DEMO_PASSWORD=*** uv run python scripts/seed_demo.py
```

前端侧对应命令：`cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build`（当前 9 files / 35 tests）。

## 8. 当前可以延后

SSE（BE-010）、单题重生成/质量反馈（BE-015）、同组公式结构去重（BE-022）、MySQL 兼容（BE-011）、admin（P1）、BYOK（P1，前端已降级）。都不在 11.29 演示关键路径上。

## 9. 待拍板（回复一句即可）

1. 时间格式：演示前保持两套口径（推荐），还是统一补 `Z`？
2. 种子生成题题型：按父题派生（推荐）/ staging 现场重生成 / 接受现状？
3. BYOK 是否在演示前实现？若实现，按 §3 的字段。
4. staging 用 SQLite 还是 MySQL（推荐 11.14 前 SQLite + WAL）。
