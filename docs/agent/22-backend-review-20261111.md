> owner: 霹雳马桶 · last_updated: 2026-11-11 · read_when: 后端 5 个 open PR 合并前对接 / 复核

# 后端产出 review 对接单（2026-11-11）

对象：人机（@zhouyuliang0606）当前 5 个 open PR。
基线：`main @ dba912d`。本文所有行号均为**分支版本**行号。

| PR | 分支 | 内容 | 分支 HEAD |
|---|---|---|---|
| #64 | `feat/be-018-drafts` | 草稿 GET/PUT/DELETE `/drafts/me` | `6b521fb` |
| #62 | `feat/be-013-stats` | 统计 `GET /stats/overview` | `64316c8` |
| #58 | `feat/be-026-generation-preferences` | 生成偏好 + strict 题型校验 | `46d424f` |
| #65 | `feat/be-009-openapi` | OpenAPI 快照 + CI 防漂移 | `2b1f1a8` |
| #63 | `fix/be-008-seed-followup` | 种子修正 + 口令注入 + reset | `2ef66b8` |

**结论：1 个阻断（#63），其余 4 个修完即可合；#65 必须最后合。**
不建议按当前状态直接合并任何一个（会立刻制造冲突或 CI 红灯）。

> **状态更新（2026-11-11 晚）**：#63 / #64 / #62 已合并（`9ecdca0` / `b2219d4` / `4a6004b`），合并前均通过 ruff + pytest + CI；#58 代码已修但仍有整文件行尾改动，待归一后合；#65 按作者要求最后合并并重新导出快照。下文结论保留为审查记录。

---

## 0. 已执行的验证（不是纸面 review）

在临时 worktree 按 #64 → #62 → #58 → #65 → #63 合并后：

| 验证 | 结果 |
|---|---|
| `pytest -q`（main 基线） | 167 passed |
| `pytest -q`（5 分支全合） | 197 passed |
| `ruff check app tests` | 通过 |
| `alembic upgrade head → downgrade base → upgrade head` | 通过（全新 SQLite；已有数据的库另验证通过） |
| `seed_demo.py`（迁移后空库） | 12 题 ×2、练习 24/21 条、覆盖 10 天、三种题型；重跑 0 新增；`--reset` 重建正常 |
| HTTP 冒烟（TestClient） | drafts 204/200/409/204、stats 字段齐全、preferences 默认 true、跨用户隔离正常 |
| GitHub Actions（5 个 PR，API 补查） | #58/#62/#63/#64/#65 的 backend + frontend 全部 success（各分支最后一轮） |
| `export_openapi.py --check`（全合后） | **失败**：快照需 +398 行 |
| 合并冲突 | #62 与 #64 冲突 `main.py` + 05/06；#58 冲突 `main.py` + 04/05（整文件）；#63 冲突 04 |

本地未复现：MySQL 实例（无实例）、真实 LLM strict 一致率（无 key）。
`gh` 是 GitHub CLI——本机没装，只影响我在终端拉 PR checks/logs，不代表 CI 没跑；已改用 GitHub API 补查，5 个 PR 当前均绿。
GitHub CI 与 LLM strict 一致率这两项人机已实测；MySQL 仍待 staging 验证。

---

## 0.1 已确认无问题（可以放心依赖）

**功能（已实跑）**

- 5 分支全合并后 197 tests 通过、ruff clean；各 PR 的 backend + frontend CI 均 success。
- 草稿：GET/PUT/DELETE 与前端契约一致（204/200/409/204）；旧 version PUT 返回 409 `DRAFT_VERSION_CONFLICT`；A/B 两账号各自一份，互不可见。
- 统计：种子库上 `total_questions=12`、`total_generated_questions=3`、练习 24/21、accuracy 0.667、最近 7 天趋势、Top5 薄弱点；空账号返回全 0，删父题后其生成题不计入。
- 偏好：GET 默认 `true`、PUT 可持久化、`StrictBool` 拒绝 `"yes"/"1"`；strict 校验集中在 `validate_segment`，失败走既有 `AI_INVALID_OUTPUT`，重试有界，不会死循环。
- 种子：12 题 ×2、答案逐题复算正确、choice/blank/solve 齐全、练习覆盖 10 天；重复执行 0 新增，`--reset` 可重建。
- OpenAPI：导出确定性（`sort_keys`、LF、无时间戳/servers），`--check` 能正确报告漂移。

**架构**

- routers 薄 → services 业务 → schemas 出参，与既有模块一致；错误统一走 `ApiError` + `{detail:{code,message,request_id}}`。
- 迁移链线性：`7d155a41e345 → 3f9c1a7e5b24 → c8e1b6a4d902`；全新库与已有数据库的 upgrade/downgrade 均验证通过。
- 所有查询按 `user_id` 收口；questions/drafts/generated 的软删语义明确；没有前端直连 LLM 的路径。
- 新增字段都有回退默认（偏好列为 NULL 时按 `true` 返回），不靠调用方猜。

**安全 / 私密信息**

- 5 个 PR 未新增 `.env`、数据库文件、私钥、证书；`.env.example` 只有空值/占位符。
- 全分支扫描无真实 `sk-*` API Key（命中的都是 CSS 类名如 `task-row__segments-head`）；文档里的 `LLM_API_KEY=sk-...` 是占位符。
- OpenAPI 快照只声明 `HTTPBearer`，无凭据；AI Key 只在服务端配置（BYOK 尚未实现）。
- 演示口令 `password123` 是公开约定，不算真实凭据；`start-dev.bat` 的 JWT secret 是本地 dev 值，生产必须替换。
- 种子脚本不打印口令；错误信息不包含密钥。

> 以上"无问题"指功能/架构/安全层面可依赖；合并前仍需处理第 1、2 节的阻断与应修项（尤其 #63 的 env 读取）。

---

## 1. 阻断项（P0，必须改完再合）

### P0-1（#63）`APP_ENV` / `DEMO_PASSWORD` 只读进程环境，不读 `.env`

- 位置：`backend/scripts/seed_demo.py:61-64`；`backend/.env.example:56,58`；`backend/app/core/config.py:8-9`。
- 事实：脚本用 `os.getenv(...)`；pydantic-settings 读 `.env` 但**不写回 `os.environ`**，仓库内无 `load_dotenv`。
- 后果：
  - `APP_ENV=production` 只写在 `.env` → 守卫失效，`--reset` 能在生产库删账号；
  - `APP_ENV` 未设置 → fail-open；
  - `DEMO_PASSWORD` 只在 `.env` → 静默回落公开的 `password123`；
  - 若以空值导出（`DEMO_PASSWORD=`）→ 创建空密码账号（`LoginRequest` 无长度校验）。
- 修法（二选一）：
  1. 在 `Settings` 增加 `app_env` / `demo_password`，脚本从 `settings` 读；
  2. 脚本启动时 `load_dotenv()`（依赖已由 pydantic-settings 间接安装）。
  然后：空值视为缺失；`APP_ENV != development/local` 且未显式给 `--yes` 时拒绝；`DEMO_PASSWORD` 缺失时 `SystemExit`，不再有默认值。
- 验收：
  - `.env` 里写 `APP_ENV=production`，不导出到 shell，运行 `python scripts/seed_demo.py --reset` 必须退出；
  - 不设 `DEMO_PASSWORD` 必须退出，不能建出 `password123` 账号。

---

## 2. 合并前应修（P1）

### #64 草稿

- [ ] **CORS 缺 PUT**：`backend/app/main.py:44` 为 `["GET","POST","PATCH","DELETE"]`，这是 API 第一个 PUT。加 `"PUT"`（否则跨域部署预检失败；当前被 Vite 代理掩盖）。
- [ ] **乐观锁非原子**：`draft_service.py:50-56` 读-比较-写，两个同 `base_version` 的并发请求都成功、后写覆盖。改为 `UPDATE ... WHERE user_id=? AND version=?` 判 `rowcount`（或 MySQL `FOR UPDATE`）。
- [ ] **并发首次保存 500**：`draft_service.py:45-48` + `models/draft.py:20` 唯一约束，输家抛 `IntegrityError` → 通用 500。捕获后回读并返回 409。
- [ ] **GET 无 response_model**：`api/v1/drafts.py:28-36` 返回裸 `Response`，OpenAPI 没有 200 schema（#65 快照里会缺形状）。用 `responses={200: {"model": DraftOut}, 204: ...}` 或返回 `DraftOut | None`。
- [ ] **产品文档未同步**：`docs/product/06-draft-dual-write.md:43` 说 409 返回服务端最新草稿、`:98` 说 200KB；实现是"不回传 + 256KB"（05 已改，06 没改）。按优先级规则（交互/验收以 PRD 为准）需二选一并改文档，不能只留 05。
- 验收补充：并发两个同 `base_version` 的 PUT，必须一个 200、一个 409；GET 在 OpenAPI 里有 schema。

### #62 统计

- [ ] **04-todos 未更新**：`docs/agent/04-todos.md:168` 仍写 BE-013 `TODO`，违反 AGENTS.md"改契约至少同步 04/05/06"。
- [ ] **全量加载 + 多余查询**：`stats_service.py:91-115` 每次请求把 questions/generated/records 全量拉成 ORM；`models/records.py:31` 的 `lazy="selectin"` 还会为每条练习再查一遍 generated。至少 `noload` + `load_only`，或改 SQL 聚合。
- [ ] **漏测分支**：`tests/test_stats_api.py:63-64` 的 `deleted=True` 从未使用；`stats_service.py:106-110` 的 `item.deleted_at is None` 改坏也无人发现。补"父题活着 + 生成题软删"用例。
- 需要前端跟进（不算后端缺陷）：mock 补 7 天且在 UTC 切天，后端稀疏 + UTC+8；mock 还按未软删过滤。演示与 mock 验收会不一致，建议开 FE issue。
- 验收：新用户返回全 0 而非 500；删父题后 `total_generated_questions` 不包含其生成题；补测后 `pytest` 通过。

### #58 生成偏好 / strict

- [ ] **EOL 洗文件（最高优先级）**：`04-todos.md` 231/231 行、`05-architecture.md` 1203/1180 行是 CRLF→LF 假改动；`--ignore-cr-at-eol` 后只剩 1/1 和 35/12。main 是 CRLF、分支是 LF，导致与 4 个在飞 PR 整文件冲突。二选一：把两份文件重新存回 CRLF；或先合 `.gitattributes` 规范化分支（#54）再 rebase。
- [ ] **`updated_at` 语义错误**：`api/v1/settings.py:21` 返回 `owner.updated_at`，而 `auth_service.py:107-108` 每次登录都写 `last_login_at`，`TimestampMixin` 的 `onupdate` 会刷新它。结果：设置页"最近更新"会在登录后跳变。迁移未合，建议同一迁移加 `preference_updated_at` 并返回它。
- [ ] **strict 失败文案不可用**：`validator.py:386-390` 的提示被 `pipeline.py:67` 包成"重试 0 次后输出仍不合法：……请在个人设置里关闭该开关"。改成面向学生的短句（如"该段未能按原题题型出题，可点重试"），设置提示留在文档/UI。
- [ ] **测试没验证 requeue**：`tests/test_settings_api.py:125-138` 手动把每个 task 执行两遍，`_fail_or_requeue` 即使直接置 failed 也能过。改为第一遍后断言 `status == queued` 且 `retry_index == 1`，再消费队列断言 failed。
- [ ] **文档同步**：`06-file-tree.md:55-56` 未列 `api/v1/settings.py`、`schemas/settings.py`、迁移、测量脚本；`05-architecture.md:921` 仍写 `generate_v2`；`:1200` 新增的 v0.6.7 行称"7 个队列测试显式关掉开关"，与最终代码和 v0.6.9 行矛盾。
- [ ] **种子数据与默认 strict 冲突（跨 PR）**：`seed_demo.py:238-241` 生成的卡片一律 `question_type="solve"`，而 6/12 原题是 choice/blank。合并后演示账号 strict=ON，但种子数据自己违反该不变量。按父题 `question_type` 派生。
- 验收：登录后设置页"最近更新"不因登录变化；strict 失败卡片文案不含"重试 0 次"；`test_tasks.py` 恢复一个 choice/blank 原题的混合题型用例。

### #65 OpenAPI 快照

- [ ] **快照把 422 当契约，运行时是 400**：16 处 `422 → HTTPValidationError`（如 `openapi.json:1656-1665`），但 `errors.py:87-100` 把校验错误映射为 400 + `{detail:{code,message,request_id}}`；快照里 400/401/404/409 全缺。给路由补 `responses`，或在 `contracts/openapi/README.md` 显著标注"真实错误信封以此为准，生成物中的 422 无效"。
- [ ] **关键响应无 schema**：`GET /tasks`（`openapi.json:2428-2435`）、`POST /questions/{id}/analyze`、`/generate` 都是 `additionalProperties: true`，因为 `tasks.py` 返回 `dict`。类型生成对最常轮询的接口没有价值，建议补 `response_model`。
- [ ] **稳定性未完全钉死**：`export_openapi.py:24` 只固定了 `LLM_MOCK`；`PROJECT_NAME` / `VERSION` / `API_PREFIX` 仍可被本机 env 覆盖，导致本机导出与 CI 不一致。导出前一并固定。
- [ ] **合并顺序**：快照不含 drafts/stats/settings；其余 PR 合入后 `--check` 必红（实测 +398 行）。**#65 最后合，合完重跑导出并提交。**
- 验收：`python scripts/export_openapi.py --check` 在最终 main 上通过。

### #63 种子（除 P0 外）

- [ ] **reset 先提交删除再重建**：`seed_demo.py:338-346`，重建失败即只剩空账号。改为同一事务，或先备份；加 `--yes` 确认；打印目标库（不含密码）。
- [ ] **练习记录全有或全无**：`:271-274` 只要存在 1 条就跳过全部补齐，staging 上点过一次练习后趋势只剩一天。改为按 `(generated_question_id, created_at)` 去重补齐。
- [ ] **seed 不写草稿**：`--reset` 会删草稿（`:320`），但脚本从不创建；BE-018 合并后草稿演示仍为空。要么种一条，要么在文档里明确"草稿不种"。
- [ ] **文档/前端仍在公示 `password123`**：`backend/README.md:60` 快捷命令没带 `DEMO_PASSWORD`；`deploy/README.md:18` 的 reset 命令也没有；`frontend/src/views/LoginView.vue:174-176` 把 `student01 / password123` 写死在登录页。staging 换真口令后必须同步（至少改成"口令见演示手册"）。
- 验收：`--reset` 中途失败不会留下空账号；重复执行练习补齐不重复；登录页不再写死演示口令。

---

## 3. 合并顺序（已验证冲突）

0. 先合 **#54 `.gitattributes` 规范化**（若不上 #54，则 #58 必须先把两份文档存回 CRLF）。
1. **#64**（同时补 CORS PUT、乐观锁）。
2. **#62**（补 04-todos、补测）。
3. **#58**（EOL 修完再合）。
4. **#63**（P0 修完）。
5. **#65 最后**：rebase 后重新导出快照；否则合完后 main 的 `OpenAPI snapshot` 步骤会红。

理由：#62/#64 都改 `main.py` 路由注册；#58 整文件行尾改动会撞所有同文件；#65 的快照是全局产物，任何后合入的路由都会让它过期。
注意：5 个 PR **各自**的 CI 目前都是绿的；下面是合并顺序，目的是避免合完把 main 弄红，不是修各自的 CI。

每个 PR rebase 后跑同一套：

```bash
cd backend
uv run ruff check app tests
uv run pytest
uv run python scripts/export_openapi.py --check   # 仅 #65 或最终 main
```

---

## 4. 需要一起拍板的口径（不要默默实现）

1. **strict 默认 ON vs 三段必须填满**：机制上不冲突（单段失败是正常终态），但"三格满"从保证变成概率。决定：默认 ON 是否保留？失败卡片是否自动降级为 soft 重试一次？
2. **409 语义**：返回服务端最新草稿（product/06）还是不回传（当前实现）？二者只能留一个，需改 06 或改代码。
3. **草稿上限**：200KB（product/06）还是 256KB（实现/05）？
4. **偏好 `updated_at`**：新建 `preference_updated_at`，还是从契约里删掉该字段由前端本地提示？
5. **统计趋势**：稀疏（当前/05）还是补零 7 天（前端 mock）？决定后同步 mock 与契约。

---

## 5. 回执模板（贴到对应 PR 或本文件末尾）

```text
PR #xx 已处理：
- [P0/P1-序号] 结论：已修 / 不改（原因）/ 转 issue
  提交：<sha>
  验证：<命令 + 结果>
遗留：<需要霹雳马桶确认的口径 / 需要前端跟进的点>
```

改完后把本文件的复选框勾上，并在 PR 描述里附 `pytest` 输出与 `--check` 结果；#65 额外附 `git diff --stat contracts/openapi/openapi.json`。

---

## 6. 前端待办（已写入 `04-todos.md` §1.9）

| ID | 任务 | 依赖 | 验收 |
|---|---|---|---|
| FE-032 | 真接口联调：练习 / 图片 / 草稿 / 统计 / 偏好 | 后端 PR 合并 | 关 mock 后练习提交/查询、图片上传/from-image、草稿 204/200/409/204、统计数字/空态/7 天趋势、偏好默认 true 且刷新仍生效 |
| FE-033 | 统计 mock 与真实契约对齐 | 无 | mock 改 UTC+8 + 稀疏（或前端补 7 天占位，与后端拍板一致）；生成题计数排除已删父题 |
| FE-034 | 设置页时间显示修复 | 无 | 无时区串补 `Z`；"最近更新""注册时间"与 UTC+8 一致；补 Vitest |
| FE-035 | BYOK 降级 + 演示口令收口 | BE-020（未实现） | `/settings/ai` 404 时设置页不崩；登录页不再写死 `student01/password123` |

> 顺序建议：FE-034 可立即做；FE-033 在"稀疏 vs 补零"拍板后做；FE-032 等后端合并；FE-035 演示前完成（BYOK 不进主路径，但不能让设置页报错）。
