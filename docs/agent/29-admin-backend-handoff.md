# 29 · Admin 后端实现交接

> 给后端同学：本文是管理端前端的后端实现交接单。
> 前端代码：`admin/`；实现级字段合同：`admin/API_CONTRACT.md`；前端实际调用：`admin/src/api/admin.ts`。
> 产品边界：`origin/docs/admin-console-plan` 分支的 `docs/agent/28-admin-console.md`、`docs/adr/ADR-009-admin-in-demo.md`。
> 当前状态：前端已完成 API 接线；后端 `/api/v1/admin/*` 尚未实现；当前前端登录使用本地演示模式。

## 1. 先看什么

1. `admin/API_CONTRACT.md`：每个接口的请求/响应字段、示例和边界。
2. `admin/src/api/admin.ts`：前端实际调用路径、query 参数和类型。
3. `admin/src/types.ts`：前端期望的 DTO。
4. 本文：数据库、权限、审计、流程、验收和联调顺序。

如果文档与代码冲突：以 `admin/src/api/admin.ts` 的实际调用为准，同时更新 `admin/API_CONTRACT.md`，不要只改一边。

## 2. 当前现状

- 后端已有学生端：JWT 登录、错题、生成任务、练习、AI 日志、统计、健康检查。
- 后端还没有：
  - `users.role`
  - `require_admin`
  - `/api/v1/admin/*`
  - `password_reset_requests`
  - `admin_audit_logs`
  - 内容审核字段
  - 管理员 seed
- 前端当前用 `VITE_ADMIN_DEMO=true` 的内存演示模式；真实联调前必须关闭该模式。
- 当前 `GET /api/v1/admin/system` 返回 404，这正说明 admin 路由还未实现。

## 3. 必须新增的数据结构

### 3.1 `users`

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | VARCHAR(16) NOT NULL DEFAULT 'student' | `student / admin` |
| `disabled_at` | DATETIME NULL | 禁用时间 |
| `disabled_reason` | VARCHAR(255) NULL | 禁用原因 |
| `must_change_password` | BOOLEAN NOT NULL DEFAULT false | 临时密码登录后强制改密 |
| `temp_password_expires_at` | DATETIME NULL | 临时密码过期时间 |

要求：

- 注册只能产生 `student`；管理员只能由 seed/环境变量/服务器脚本创建。
- `get_current_user` 拒绝已禁用账号。
- `require_admin` 每次查 DB 的 `role`，不能只信 JWT claim。
- 禁用账号时 `token_version += 1`，旧 token 立即失效。

### 3.2 `questions`

在现有表上新增：

| 字段 | 类型 | 说明 |
|---|---|---|
| `hidden_at` | DATETIME NULL | 管理员隐藏时间 |
| `hidden_reason` | VARCHAR(255) NULL | 隐藏原因 |
| `flagged_at` | DATETIME NULL | 标记异常时间 |
| `flag_reason` | VARCHAR(255) NULL | 标记原因 |

复用现有 `status`：`confirmed` = 正常展示，`hidden` = 已隐藏。
学生端错题列表/详情必须过滤 `status='confirmed'`；管理员接口要能看到 hidden。

### 3.3 `password_reset_requests`

至少包含：

```text
id
user_id                  # 命中的 student；查不到用户时不建单
username                 # 提交时的用户名快照
submitted_email          # 学生提交的邮箱，可空
reason
status                   # pending / approved / rejected
reviewed_by              # 管理员 username
reviewed_at
review_note              # 审批依据 / 拒绝原因
created_at
ip
user_agent
expires_at               # 临时密码过期时间
delivery_channel         # wechat / phone / email / other
```

索引：`(status, created_at)`、`(user_id, created_at)`。
不存临时密码明文；密码只存 `users.password_hash`。

### 3.4 `admin_audit_logs`

```text
id
actor_user_id
actor_username           # 快照，管理员改名后仍能查
action                   # user.disable / task.retry / password_request.approve ...
target_type              # user / task / question / ai_log / password_request / audit ...
target_id
target_label             # 给列表展示的快照，如 student06 / T-2041 / Q-1042
target_owner_id
before_json
after_json
reason
result                   # success / failed
request_id
ip
user_agent
created_at
```

索引：`(actor_user_id, created_at)`、`(action, created_at)`、`(target_type, target_id)`。
不记录：临时密码、密码散列、JWT、API Key、完整学生答案。

### 3.5 `admin_alert_acks`

```text
alert_key                # tasks_failed / password_pending / ai_latency / ai_error_rate
acknowledged_by
acknowledged_at
note
```

告警本身由任务、密码申请、AI 日志实时推导；ack 只记录“已确认”。

### 3.6 迁移

- 新增一个 Alembic migration，例如 `admin_console`。
- SQLite 使用 `batch_alter_table`，MySQL 不能依赖 SQLite 专用语法。
- 不要修改历史 migration。
- 更新 `app/models/__init__.py` 与 `alembic/env.py` 的 import，让 autogenerate 能看到新表。

## 4. 权限与会话

- 管理端使用独立 localStorage key：`bababoi:admin-token` / `bababoi:admin-user`。
- JWT 仍复用同一签名密钥与 `token_version` 校验链，不另造一套会话。
- 所有 `/api/v1/admin/*`（除登录）必须 `require_admin`：
  - 未登录：401
  - 学生 token：403
  - 禁用管理员：403
- 管理员登录不开放注册；不允许学生端注册出 admin。
- 管理员登录成功写 `admin.login` 审计；退出写 `admin.logout`（best-effort）。
- CORS 默认应包含 `http://localhost:5174`（admin dev）。如果 admin 使用别的端口，补进 `CORS_ORIGINS` 或通过 Vite 代理。

## 5. 接口清单

前缀统一 `/api/v1`。完整字段见 `admin/API_CONTRACT.md`。

### 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/admin/auth/login` | 管理员登录；非 admin 403；写审计 |
| GET | `/admin/me` | 当前管理员；401/403 |
| POST | `/admin/logout` | 退出；写审计 |
| POST | `/auth/password-reset-requests` | 公开提交；固定 202 泛化响应、限流、不泄露账号是否存在 |

### 总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/overview` | 用户/内容/AI/任务/密码申请聚合、失败任务、待审批、审计、告警、趋势 |

### 用户

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/users` | 列表；q/status/page/page_size |
| GET | `/admin/users/{id}` | 详情 + 最近任务 + 最近密码申请 |
| POST | `/admin/users/{id}/status` | 禁用/启用；禁用必须有 reason，写审计 |
| POST | `/admin/users/{id}/force-logout` | token_version +1，写审计 |

### 密码申请

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/password-requests` | 列表；status/q/page/page_size |
| GET | `/admin/password-requests/{id}` | 详情（可选，但建议） |
| POST | `/admin/password-requests/{id}/approve` | 生成一次性临时密码；写审计 |
| POST | `/admin/password-requests/{id}/reject` | 拒绝；写审计 |
| POST | `/admin/password-requests/{id}/regenerate-temp-password` | 重新生成，旧密码立即失效 |

### 内容

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/questions` | 列表；q/status/flagged/page/page_size |
| GET | `/admin/questions/{id}` | 全文、生成题、任务、最近审计 |
| POST | `/admin/questions/{id}/moderation` | hide/restore/flag/unflag；reason；写审计 |

### 任务

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/tasks` | 列表；status/q/page/page_size |
| GET | `/admin/tasks/{id}` | 详情 + 真实 timeline |
| POST | `/admin/tasks/{id}/retry` | 仅 failed；retry_index < 3；写审计 |
| POST | `/admin/tasks/{id}/cancel` | 仅 queued；写审计 |

### AI 日志

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/ai-logs` | 列表；status/operation/q/page/page_size；不返回 raw |
| GET | `/admin/ai-logs/{id}` | 详情；不返回 raw |
| POST | `/admin/ai-logs/{id}/raw` | 返回 raw，必须 reason，写 `ai_log.view_raw` 审计；`Cache-Control: no-store` |

### 审计

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/audit` | 列表；q/result/page/page_size |
| GET | `/admin/audit/{id}` | 详情，含 before/after |
| GET | `/admin/audit/export.csv` | UTF-8 BOM、中文表头、引号转义；写 `audit.export` |

### 告警

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/alerts` | 返回数组，不包 items；由真实数据推导 |
| POST | `/admin/alerts/{key}/ack` | 写 ack 表；写审计 |
| POST | `/admin/alerts/{key}/unack` | 删除 ack；写审计 |

### 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/system` | 真实环境、DB/API/worker/LLM 检查、只读配置、事件 |

## 6. 关键流程

### 6.1 密码重置

1. 学生 `POST /auth/password-reset-requests`，body：username、email、reason。
2. 后端永远返回 `202 {"message":"如果账号存在，申请已提交"}`；不返回 request_id，不区分账号是否存在。
3. 用户名不存在：不建单；已存在 pending：不重复建单；已有 pending 的同一用户按幂等处理。
4. 按 IP/用户名限流，具体阈值与后端确认。
5. 管理员审批：
   - 必须校验 reason >= 4 字、verified=true；
   - 目标不能是 admin，不能是 disabled；
   - 生成 12 位左右临时密码，只返回一次；
   - 写 `users.password_hash`、`must_change_password=true`、`temp_password_expires_at=now+24h`；
   - `token_version += 1`；
   - 申请状态 approved，写 reviewed_by/reviewed_at/review_note/delivery_channel；
   - 审计与重置同一事务，审计失败回滚；
   - 响应 `Cache-Control: no-store`，不存临时密码明文。
6. 重新生成：允许 pending/approved，旧临时密码立即失效，再写审计。
7. 学生用临时密码登录后，登录响应带 `must_change_password=true`。
8. 建议同时实现强制改密门禁：除 `GET /auth/me`、`POST /auth/logout`、`POST /auth/change-password` 外，其他业务接口返回 403 `PASSWORD_CHANGE_REQUIRED`；学生前端路由守卫是后续单独任务，但后端门禁不能省。
9. 改密成功清 `must_change_password` / `temp_password_expires_at`，`token_version += 1`，并回写对应密码申请的 used_at（如果表里有该字段）。

### 6.2 内容审核

- 隐藏：`status='hidden'` + `hidden_at` + `hidden_reason`。
- 恢复：`status='confirmed'`，清隐藏字段。
- 标记：`flagged_at` + `flag_reason`；不改变可见性。
- 取消标记：清标记字段。
- 原因 >= 4 字；写 before/after 审计；危险色只用于删除，不用于普通标记。
- 学生端列表/详情必须排除 hidden。

### 6.3 任务

- 管理员重试绕过 owner 校验，但仍校验状态：只有 failed，`retry_index < 3`。
- 取消只允许 queued；running 不强行中断。
- 返回最新 TaskDTO；写 before/after 审计。
- 时间线必须用真实 `created_at/started_at/finished_at`，不要再把 `createdAt.slice()` 拼回原串。

### 6.4 审计

覆盖：

- admin 登录/登出
- 用户禁用/启用/强制下线
- 密码申请通过/拒绝/重新生成
- 任务重试/取消
- 内容隐藏/恢复/标记/取消标记
- AI 原始输出查看
- 审计导出

高风险写操作与审计必须同一事务。审计写失败则操作回滚。
列表搜索要同时匹配中文动作名（如“通过密码申请”）和原始 action code。

### 6.5 告警

由真实数据推导，至少四个 key：

- `tasks_failed`：最近 15 分钟 failed 任务；阈值建议 ≥3。
- `password_pending`：pending 密码申请 > 0。
- `ai_latency`：最近 1 小时 P95 > 45 秒。
- `ai_error_rate`：最近 1 小时 error+invalid > 10%。

条件不成立就不返回该告警。`admin_alert_acks` 存在时返回 `status=acknowledged`，否则 `active`。
返回的 `target` 必须能让前端跳到 `/tasks?status=failed`、`/password-requests`、`/ai-logs`。

### 6.6 系统健康

- 环境：真实 `APP_ENV`、`LLM_MOCK`、版本、DB、worker 状态。
- 检查项：API、DB、worker/队列、LLM；值是真实探活或真实聚合。
- 不要写死 `staging` / `real`，不要写假 DEMO 数据。
- 配置只读；不展示 API Key、JWT Secret、数据库密码。
- 事件列表来自真实任务/AI 日志/审计，不要编造。

## 7. 返回字段与状态约定

完整字段以 `admin/API_CONTRACT.md` 为准。这里只列容易对错的：

- 列表：`{items,total,page,page_size}`；告警是裸数组。
- 时间：列表展示 UTC+8 字符串，如 `11-27 22:41:08`；数据库仍存 UTC naive。
- 计数：整数，不要返回 `"02"` 这种前导零字符串。
- 金额：`estimated_cost` 没有价格配置时返回 `null`，前端显示 `—`。
- 状态：
  - 任务：`queued/running/done/failed/canceled`
  - 用户：`active/disabled`
  - 密码申请：`pending/approved/rejected`
  - 内容：`active/hidden` + `flagged`
  - AI 日志：`success/error/invalid`
  - 告警：`active/acknowledged`
- `AdminProfile` 使用 `must_change_password` 字段名；其余 DTO 使用 camelCase。
- 绝不返回 `password_hash`、JWT、API Key 密文、完整 Key、临时密码明文（审批响应除外，且只一次）。

## 8. Seed 管理员

新增 `backend/scripts/seed_admin.py` 或等价服务器脚本：

- 环境变量：`ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_EMAIL`。
- **无默认密码**；缺失直接退出。
- 生产环境拒绝运行；`--reset` 需要显式确认。
- 创建/更新 `users.role='admin'` 的账号；不通过公开注册创建 admin。
- 不把密码写进仓库、日志、审计。
- 管理员忘记密码不做 UI 自助；只能服务器 shell 重新 seed 或运维脚本重置。

## 9. 验收

后端完成后至少验证：

- [ ] 学生 token 访问 `/api/v1/admin/*` 返回 403；admin token 200。
- [ ] admin 登录成功；非 admin/禁用账号 403。
- [ ] 总览数字与 DB 一致：用户、内容、AI 调用、失败任务、待审批。
- [ ] 用户禁用后旧 token 失效、登录被拒；启用后可登录。
- [ ] 密码申请：提交 202 泛化、去重、审批、临时密码 24h、重新生成、拒绝、审计。
- [ ] 临时密码不出现在日志/审计/数据库明文。
- [ ] 内容隐藏后学生端不可见；管理员仍可见；标记不改变可见性。
- [ ] 任务重试/取消状态正确，写审计；running 不可取消。
- [ ] AI 原始输出必须带 reason，写审计；列表/详情默认不含 raw。
- [ ] 审计列表、详情、CSV 导出可用；before/after 真实；CSV 中文不乱码。
- [ ] 告警由真实数据生成；ack/unack 可逆；侧栏/总览/告警页计数同源。
- [ ] 系统健康不返回假环境；不泄露密钥。
- [ ] 现有学生端测试全部通过；OpenAPI 快照按项目流程更新。

## 10. 前端联调

前端位置：`G:\AIworkspace\opencode\BababoiLearningMachine\admin`。

- 真实 API 调用：`admin/src/api/admin.ts`。
- 演示模式：`admin/.env.local` 中 `VITE_ADMIN_DEMO=true`；联调前改成 `false` 或删除该文件。
- 演示登录账号：`admin / admin123`，只用于本地看页面。
- 前端 Vite 默认 `5174`，代理 `/api` 到 `127.0.0.1:8000`。
- 后端实现后，先打开 `http://127.0.0.1:5174/admin/login` 用真实管理员账号登录，再逐个页面刷新；不要保留演示数据做验收。
- 接口字段有变化时，同步更新 `admin/API_CONTRACT.md` 和 `admin/src/types.ts` / `admin/src/api/admin.ts`，不要只改后端。

## 11. 明确不做

- 教师端、班级/作业/家校沟通。
- 完整 RBAC、多租户、组织架构。
- 邮件/短信自动发送；临时密码仍由管理员线下告知。
- 学生状态查询页、模拟登录、SQL 控制台。
- 物理删除、批量导出 PII、批量禁用。
- Prometheus/Redis/ELK/webhook；MVP 用 DB 聚合 + `/health`。

## 12. 待确认默认值

1. 管理员 token TTL（建议 8h，或复用学生 7 天）。
2. 审计保留天数（建议 180 天）。
3. 密码申请限流阈值（建议 3 次/天/IP+用户名）。
4. `ai_call_logs` 是否补 `task_id` / `request_id`（当前合同未强制，但强烈建议）。
5. 告警阈值是否采用本文的 3 个 / 45s / 10%。
6. 内容软删除是否在 P1 真正实现；若暂无，不要在前端/文案承诺“删除”，只做隐藏/标记。

## 13. 相关文件

- `admin/API_CONTRACT.md`：完整接口字段与示例
- `admin/src/api/admin.ts`：前端实际调用
- `admin/src/types.ts`：DTO
- `admin/src/stores/adminData.ts`：数据源与刷新逻辑
- `admin/src/stores/auth.ts`：管理员登录/Session
- `origin/docs/admin-console-plan` 分支的 `docs/agent/28-admin-console.md`：产品/范围
- `origin/docs/admin-console-plan` 分支的 `docs/adr/ADR-009-admin-in-demo.md`：演示范围决策
- `docs/adr/ADR-010-scope-roles-types-subjects-stages.md`：角色/密码重置边界

## 14. 给后端同学的最短路径

1. 先做 role/disabled/require_admin + seed 管理员 + admin 登录/me。
2. 再做 audit + password_reset_requests 两张表。
3. 再做 overview、users 只读、tasks、ai-logs、system 只读；先让总览和排障页跑通。
4. 再做密码审批、用户禁用、内容审核、任务重试/取消。
5. 最后做 alerts、导出、搜索/分页细节。
6. 每完成一组，通知前端把 `VITE_ADMIN_DEMO` 关掉做一次真实联调。
