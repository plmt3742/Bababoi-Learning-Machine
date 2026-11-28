---
owner: 霹雳马桶
last_updated: 2026-11-28
status: active
read_when: 开发/联调 admin 管理端前；评审监控、审计、密码重置时
---

# 28 · Admin 管理端规划与后端对接

> 决策：ADR-005（独立管理端）+ ADR-009（进入 11.29 演示）。
> 前端：独立 `admin/` 应用；后端：`/api/v1/admin/*`，全部 `require_admin`（登录与公开密码申请除外）。
> 本文是管理端的详细方案与后端对接单；实现后以 OpenAPI 与代码为准，冲突时按 AGENTS 的事实来源优先级处理。

## 1. 定位与演示范围

### 1.1 定位

管理端是**内部运维台**，不是教师端，也不是完整后台管理。它回答五个问题：

1. 系统现在是否正常？
2. AI 分析/生题的成功率、延迟、成本如何？
3. 哪些任务失败、为什么、能否重试？
4. 哪条错题/生成题内容有问题？
5. 谁在什么时候做了什么操作？

### 1.2 11.29 演示范围

**管理端进入 11.29 演示**（ADR-009），但演示只承诺已实现的能力，未完成项不伪装。

| 优先级 | 演示内容 |
|---|---|
| 必须 | 管理员登录/403 边界、总览、任务列表/详情（只读）、AI 调用日志（只读）、审计列表、系统健康 |
| 目标 | 线上密码申请 + 管理员审批 + 临时密码 24h + 学生强制改密 |
| 演示后 | 用户管理（列表/禁用/强制下线）、任务重试/取消、内容标记/质量队列、导出、告警中心、批量操作、只读 auditor、完整审计保留策略 |

> 若密码申请的后端基础（role/audit/request）在演示前未完成，只在 PPT 中讲流程，不在现场演示写操作。总览/任务/AI 日志/审计/健康若未完成，也只放已实现的只读页面或 PPT，不用假数据填充。
>
> 11.28 晚做一次冻结判定：必须项没完成的，演示时只展示已实现部分并在 PPT 标注规划；管理端不得反向阻塞学生端。
>
> 当前后端只完成 ADM-002/009（#123）；admin 前端页面在 PR #120（未合）。`VITE_ADMIN_DEMO` 的假数据只用于本地看页面，不得用于 11.29 现场演示。

### 1.3 不做

- 教师端、班级/作业/家校沟通。
- 完整 RBAC、多租户、组织架构。
- 用户模拟登录、直接 SQL 控制台、物理删除。
- 批量导出学生个人数据。
- 邮件/短信通知；临时密码由管理员通过现有外部渠道通知学生。
- MVP 阶段 Prometheus/Redis/ELK；先用 DB 聚合 + `/health` + 结构化日志。

## 2. 已确认决策

| 决策 | 内容 |
|---|---|
| 管理端形态 | 独立 `admin/` Vue 3 + Vite + TS + Arco；独立登录页与 `bababoi:admin-token` |
| 权限 | `users.role = student \| admin`；单 admin 角色；`require_admin` 每次查 DB |
| 账号字段 | **不新增姓名/学号**；沿用 `username`、可选 `email`、`password` |
| 密码重置 | 学生线上申请 → 管理员审批 → 临时密码只在管理端显示一次 → 24h 有效 → 学生登录后强制改密 |
| 通知 | 没有邮件/短信；管理员通过班级群/微信/电话等外部渠道通知 |
| 学生状态页 | 不做；提交后只显示“等待管理员联系” |
| 审计 | 所有管理员写操作 + 敏感读取 + 导出；append-only |
| 监控 | DB 聚合 + `/health`；不引入新基础设施 |

> 与 ADR-010 的关系：角色/题型/学科/学段边界一致；密码重置的定稿流程以 ADR-010 §2.1 与本文 §5 为准（2026-11-27 补正后一致），包括 202 泛化响应、强制改密门禁与临时密码重新生成。

## 3. 信息架构

### 3.1 管理端页面

| 页面 | 路径 | 内容 |
|---|---|---|
| 登录 | `/admin/login` | 管理员登录；非 admin 403 |
| 总览 | `/admin` | 业务/AI/任务/内容/系统健康 |
| 告警 | `/admin/alerts` | 真实数据推导的告警、确认/取消确认 |
| 用户 | `/admin/users` | 列表、搜索、禁用/启用、详情 |
| 密码申请 | `/admin/password-requests` | 待审批、通过、拒绝、审计 |
| 内容 | `/admin/questions` | 错题/生成题列表、详情、隐藏/恢复、标记 |
| 任务 | `/admin/tasks` | 队列、筛选、详情、重试/取消 |
| AI 日志 | `/admin/ai-logs` | 调用列表/详情、raw 单独接口 |
| 审计 | `/admin/audit` | 操作日志、筛选、详情、导出 |
| 系统 | `/admin/system` | 健康、版本、环境、只读配置 |

侧边栏分组：监控（总览/告警）、运营（用户/内容）、AI 运维（任务/AI 日志）、审计、系统。

### 3.2 学生端相关页面

| 页面 | 路径 | 内容 |
|---|---|---|
| 忘记密码 | `/forgot-password` | 提交线上申请；不要求登录 |
| 设置 | `/settings` | 临时密码登录后强制改密；现有改密卡 |

## 4. 功能模块

### 4.1 监控总览

| 组 | 指标 |
|---|---|
| 用户 | 总数、近 7 天活跃（`last_login_at`）、禁用数 |
| 内容 | 错题数、生成题数、练习记录数、平均正确率、标记/软删数 |
| AI | 调用量、成功率、error/invalid 率、p50/p95 延迟、队列等待、tokens、估算成本 |
| 维度 | operation、model、prompt_version、key_source、type_policy |
| 任务 | queued/running/failed/canceled、最老排队、失败率、重试率 |
| 系统 | `/health`、`/ready`、DB、LLM 模式、worker、版本/环境 |

时间范围：`1h / 24h / 7d / 30d`；UTC 存储，展示 UTC+8。仪表盘缓存 30–60 秒，返回 `generated_at`。

### 4.2 任务与 AI 运维

- 任务列表：按状态、stage、错误码、用户、题目、时间筛选；服务端分页。
- 任务详情：时间线、错误、关联题目、AI 调用（没有 `ai_call_logs.task_id` 时按 `question_id` 聚合，见 §6.4）、raw 入口。
- 操作：失败重试、排队取消；running 不强行中断；管理员重试绕过 owner 校验但校验状态并写审计。
- AI 日志：operation/model/status/latency/tokens/key_source/error；列表不返回 raw。
- raw 输出：单独接口，截断 8k，访问写审计。
- 成本：token × 模型单价估算；标注“估算”，不做真实计费。
- 识图缓存：MVP 只读统计；P2 再考虑清理。

### 4.3 用户

- 列表：用户名、邮箱（脱敏）、角色、状态、错题/生成题/练习数、最近登录。
- 详情：账号资料、统计、最近任务、AI 设置状态（provider/model/key_last4，不显示 Key）。
- 操作：禁用/启用、强制下线、密码申请审批。
- 禁用：`disabled_at` / `disabled_reason` + `token_version += 1`；旧 token 失效；登录/业务接口 403 `ACCOUNT_DISABLED`。
- 非管理员访问 `/admin/*` 返回 403 `ADMIN_REQUIRED`。
- 禁止禁用自己、禁止禁用最后一个 active admin。

### 4.4 内容

- 错题列表：题干摘要、用户、学科、题型、掌握状态、隐藏/标记、时间。
- 错题详情：全文、选项/空位、答案/解析、AI 分析、生成题、图片、练习次数、任务历史。
- 生成题：父题、target_index、难度、validation_status/score、model/prompt_version、标记。
- 操作：隐藏/恢复（`questions.status='hidden'` + `hidden_at`/`hidden_reason`）、标记/取消标记（`flagged_at`/`flag_reason`）；不做富文本编辑。
- 图片：详情返回 `imagePath`；admin 读取走受保护接口，具体端点随 ADM-006 定，不暴露 `uploads/` 静态路径；查看写审计。
- 质量队列：invalid/fallback/低分/被标记；Phase 3 做只读队列，Phase 4 完整工作流。

### 4.5 系统

- 健康：`/health`、`/ready`、DB、LLM 模式、worker、版本/环境、上传目录磁盘占用。
- 配置：只读展示任务并发、重试上限、硬超时、图片限制、分页上限、BYOK 是否启用。
- 配置变更走部署/环境变量，不在 admin UI 直接改 `.env`。
- 演示 seed 状态可展示；重置演示数据只走脚本，不放进 UI。

## 5. 线上密码重置（定稿）

### 5.1 流程

1. 学生登录页点“忘记密码”，进入 `/forgot-password`。
2. 填写：`username`、注册邮箱（可选）、申请原因。
3. 后端对任何提交都返回同一个 **202 泛化响应**（不返回 `request_id`、不区分账号是否存在）；内部：用户名不存在则不落库；存在且已有 pending 则不重复建单（对外表现为幂等 202；并发由 §6.2 唯一约束兜底，冲突也返回 202）；存在且无 pending 才建单；按 IP/用户名限流。
4. 命中时创建 `password_reset_requests`，状态 `pending`；未命中不建单。
5. 管理员在 `/admin/password-requests` 核对用户名/邮箱/账号状态；填写核验说明（必填，记录核验方式）；拒绝时填写拒绝原因。
6. 通过后：生成临时密码、bcrypt 入库、`must_change_password=true`、`temp_password_expires_at=now+24h`、`token_version += 1`、写审计。
7. 管理端弹窗只显示一次临时密码；管理员通过外部渠道通知学生。
8. 学生用临时密码登录；登录响应 `must_change_password=true`。
9. 前端强制跳转设置页改密；后端按 §5.4 的 `require_password_ready` 门禁拦截其他业务接口。
10. 学生用临时密码 + 新密码改密；清标记/过期时间、`token_version += 1`、审计；当前登录退出，用新密码重新登录。

### 5.2 边界

- 不做学生状态查询页、不做自助领取临时密码、不做邮件/短信。
- 临时密码由后端生成（12 位左右，去除易混淆字符），每次审批/重新生成响应只返回一次；`Cache-Control: no-store`。
- 不写日志/审计/数据库明文；管理端不持久化；关闭弹窗即清空。
- 临时密码 24h 有效；过期后登录返回 403 `TEMP_PASSWORD_EXPIRED`，已登录会话访问业务接口或 `/auth/change-password` 同样返回 403 `TEMP_PASSWORD_EXPIRED`；`GET /auth/me`、`POST /auth/logout` 仍放行，学生重新申请。
- 管理员忘记临时密码只能重新生成；旧临时密码立即失效。重新生成端点见 §5.3；审批响应丢失时也用它恢复，不重复审批。
- 管理员账号、禁用账号、审批人自己的账号不建单（提交端仍返回 202，不暴露账号状态）；若历史脏数据里出现这些目标，审批动作返回 409 `RESET_REQUEST_STATE_INVALID`。
- 审计与重置同一事务；审计写失败则回滚，不生成临时密码。

### 5.3 接口

```http
POST /api/v1/auth/password-reset-requests
{ "username": "student01", "email": "student01@example.com", "reason": "忘记密码" }
```

响应固定为 `202 Accepted`，body 例如 `{ "message": "如果账号存在，申请已提交" }`；不返回 `request_id`，不区分账号是否存在。

```http
GET  /api/v1/admin/password-requests?status=pending|approved|rejected|all
GET  /api/v1/admin/password-requests/{id}
POST /api/v1/admin/password-requests/{id}/approve
POST /api/v1/admin/password-requests/{id}/reject
POST /api/v1/admin/password-requests/{id}/regenerate-temp-password
```

通过/重新生成响应（每次只返回一次）：

```json
{
  "request": { "id": 301, "status": "approved" },
  "temporary_password": "K7m2P9q4R6s8",
  "must_change_password": true,
  "expires_at": "2026-11-28T22:48:00+08:00",
  "audit_id": 123
}
```

> 响应字段以 `admin/API_CONTRACT.md` §4 为准：这里用 `expires_at`；数据库字段仍是 `users.temp_password_expires_at`。

**状态与幂等**

| 当前状态 | 动作 | 结果 |
|---|---|---|
| pending | approve | 200 + 临时密码；置 approved；`token_version += 1`；写审计 |
| pending | reject | 200；置 rejected；写审计 |
| pending | regenerate | 409 `RESET_REQUEST_STATE_INVALID` |
| approved | approve / reject | 409 `RESET_REQUEST_STATE_INVALID` |
| approved | regenerate | 200 + 新临时密码；重置 `temp_password_expires_at=now+24h`；旧临时密码立即失效；`token_version += 1`；写审计 |
| rejected | 任意写操作 | 409 `RESET_REQUEST_STATE_INVALID` |

- approve/reject/regenerate 都用条件 UPDATE（`WHERE id=? AND status=?`）；并发只有一个成功，输的一方 409。
- 审批响应丢失：用 `GET /admin/password-requests?status=approved` 或 `GET /{id}` 查状态，再调用 regenerate，不重复审批。
- regenerate 只对 approved 生效；已过期也允许 regenerate，视为重新发放。
- 与 `admin/API_CONTRACT.md` §4 的差异：前端契约写的是 pending 或 approved 都可 regenerate；本方案只允许 approved，避免绕过审批核验。BE-030 实现以本方案为准，前端契约随 BE-030 同步。

### 5.4 强制改密门禁

临时密码登录成功后，登录响应带 `must_change_password=true`。在改密完成前：

- 只放行 `GET /auth/me`、`POST /auth/logout`、`POST /auth/change-password`。
- 其他业务接口一律 403 `PASSWORD_CHANGE_REQUIRED`。
- 临时密码过期（`temp_password_expires_at < now`）后，登录、业务接口与 `/auth/change-password` 返回 403 `TEMP_PASSWORD_EXPIRED`；`GET /auth/me` 与 `POST /auth/logout` 仍放行，学生需重新申请。
- 前端路由守卫读取 `must_change_password`（登录响应或 `/auth/me`），跳转 `/settings` 强制改密；`/auth/me` 必须放行，否则刷新/恢复会话会把用户踢回登录页。
- 改密成功后清 `must_change_password` 与 `temp_password_expires_at`，`token_version += 1`，当前会话也需用新密码重新登录。

## 6. 数据模型

### 6.1 `users` 新增字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | VARCHAR(16) NOT NULL DEFAULT 'student' | student/admin |
| `disabled_at` | DATETIME NULL | 禁用时间 |
| `disabled_reason` | VARCHAR(255) NULL | 禁用原因（管理员填写） |
| `must_change_password` | BOOLEAN NOT NULL DEFAULT false | 临时密码强制改密 |
| `temp_password_expires_at` | DATETIME NULL | 24h 有效期 |

**不新增姓名/学号。**

### 6.2 `password_reset_requests`

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `user_id` | 命中的学生 ID（NOT NULL；未命中不建单） |
| `username` | 提交的用户名 |
| `submitted_email` | 提交的邮箱（可选） |
| `reason` | 申请原因 |
| `status` | pending/approved/rejected |
| `reviewed_by` / `reviewed_at` | 审批管理员用户名快照/时间 |
| `review_note` | 审批备注/拒绝原因 |
| `expires_at` | 临时密码过期时间（审批/重新生成时写） |
| `delivery_channel` | 通知渠道快照（如 wechat/phone） |
| `used_at` | 学生用临时密码成功改密后回写 |
| `created_at` | 申请时间 |
| `ip` / `user_agent` | 申请来源 |

索引：`(status, created_at)`、`(user_id, created_at)`。不存临时密码、secret、明文密码。

**pending 唯一性**：同一 `user_id` 最多一条 pending。SQLite 用 partial unique index `UNIQUE(user_id) WHERE status='pending'`；MySQL 8 用生成列 `pending_user_id = IF(status='pending', user_id, NULL)` + 唯一索引（MySQL 不支持部分索引）。service 层捕获唯一冲突后仍返回 202，保证并发提交的幂等。

### 6.3 `admin_audit_logs`

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `actor_user_id` / `actor_username` | 管理员及快照；`actor_user_id` 可空（CLI/系统动作用 NULL + `actor_username='system'`） |
| `action` | user.disable / task.retry / password_request.approve / password_request.regenerate / ai_log.view_raw 等 |
| `target_type` / `target_id` / `target_label` | 目标及快照；`target_id` 统一按字符串存 |
| `target_owner_id` | 内容所属学生 |
| `before_json` / `after_json` | 脱敏 diff |
| `reason` | 可空；系统动作自动填充（如登录/登出），管理员写操作可选填 |
| `result` | success/failed |
| `request_id` / `ip` / `user_agent` | 来源 |
| `created_at` | 时间 |

索引：`(actor_user_id, created_at)`、`(action, created_at)`、`(target_type, target_id)`。

### 6.4 其他建议

- 内容审核字段（随后续 ADM 任务补迁移）：`questions.hidden_at`/`hidden_reason`/`flagged_at`/`flag_reason`；`status` 用 `confirmed`/`hidden`。**不用 `content_flags`**。
- `admin_alert_acks`：`alert_key` PK、`acknowledged_by`、`acknowledged_at`、`note`（已随 ADM-002 建表；告警本身由真实数据实时推导）。
- `ai_call_logs.task_id`（Phase 1 建议加，任务详情按 task 精确关联 AI 调用）、`ai_call_logs.request_id`（Phase 2）。
- `generation_task`：`(user_id, created_at)`、`(stage, status, created_at)`、`(error_code, created_at)`。
- `ai_call_logs`：`(created_at)`、`(status, created_at)`、`(operation, created_at)`。

## 7. API 总表

| 模块 | 端点 |
|---|---|
| 认证 | `POST /admin/auth/login`、`GET /admin/me`、`POST /admin/logout`（登录/登出写审计） |
| 监控 | `GET /admin/overview`、`GET /admin/alerts`（告警由真实数据推导，裸数组） |
| 用户 | `GET /admin/users`、`GET /admin/users/{id}`、`POST /admin/users/{id}/status`（active/disabled）、`POST /admin/users/{id}/force-logout` |
| 密码申请 | 公开 `POST /auth/password-reset-requests`（固定 202 泛化响应）；管理端 `GET /admin/password-requests`、`GET /admin/password-requests/{id}`、`POST .../approve`、`POST .../reject`、`POST .../regenerate-temp-password` |
| 内容 | `GET /admin/questions`、`GET /admin/questions/{id}`、`POST /admin/questions/{id}/moderation`（`hide/restore/flag/unflag`） |
| 任务 | `GET /admin/tasks`、`GET /admin/tasks/{id}`、`POST /admin/tasks/{id}/retry`、`POST /admin/tasks/{id}/cancel` |
| AI 日志 | `GET /admin/ai-logs`、`GET /admin/ai-logs/{id}`、`POST /admin/ai-logs/{id}/raw`（`reason` 必填 + 审计 + `Cache-Control: no-store`） |
| 审计 | `GET /admin/audit`、`GET /admin/audit/{id}`、`GET /admin/audit/export.csv` |
| 告警确认 | `POST /admin/alerts/{key}/ack`、`POST /admin/alerts/{key}/unack` |
| 系统 | `GET /admin/system` |

> 实现真源：`admin/API_CONTRACT.md`（PR #120）与 `admin/src/api/admin.ts`；本表按它们校正，不再保留早期草稿里的 `/metrics/*`、`PATCH users`、`content_flags` 等叫法。

统一：`/api/v1` 前缀、Bearer JWT、`{items,total,page,page_size}`、统一错误信封、`X-Request-ID`。写操作可带 `reason`（高风险操作建议填写），响应带 `audit_id`。

## 8. 监控口径

| 指标 | 定义 | 注意 |
|---|---|---|
| 活跃用户 | `last_login_at >= start` | 不是精确 DAU |
| AI 成功率 | success / total | error/invalid 分开 |
| p50/p95 | 范围内 latency 分位 | SQLite/MySQL 通用分位差；Python 计算或后续聚合 |
| 任务失败率 | failed / (done+failed+canceled) | 分母固定 |
| 最老排队 | now - min(created_at) where queued | 告警用 |
| 缓存命中率 | hit_count / (hit_count + vision calls) | 累计值，MVP 标近似 |
| 5xx 趋势 | 需请求指标入库 | MVP 不做，P2 加 |
| Worker 心跳 | 需 heartbeat 表 | MVP 用队列状态推断 |

## 9. 审计要求

覆盖：admin 登录/失败/登出、用户禁用/启用/强制下线、密码申请通过/拒绝/重新生成、任务重试/取消、内容隐藏/恢复/标记、raw/图片访问、审计导出、配置变更；CLI/系统动作以 `actor_user_id=NULL` + `actor_username='system'` 记录。

- 高风险写操作与审计同一事务；审计失败回滚。
- 现有 service 内部 commit 的，admin 侧需要 `commit=False` 或抽出不提交的内部函数。
- 审计不记录临时密码、secret、密码散列、API Key。
- 审计日志不提供 UI 删除；保留策略只走数据库任务。

## 10. 安全与隐私

- 管理端独立 localStorage key（`bababoi:admin-token`）与登录页；JWT 仍共用同一签名密钥与 `token_version` 校验，学生 token 403 `ADMIN_REQUIRED`，禁用账号 403 `ACCOUNT_DISABLED`；admin token 有效期单独 8h（已随 ADM-002 实现）。
- 管理端登录限流；CORS 增加 `http://localhost:5174`，生产同源。
- 除 `POST /admin/auth/login` 的 access token 外，响应不返回 JWT；任何响应都不返回 JWT Secret、`password_hash`、API Key 密文、完整 Key。
- 邮箱列表脱敏；原始 AI/图片访问审计；导出脱敏、限行数。
- 审批核验为人工外部渠道，`submitted_email` 不作为身份凭证；管理员在 `review_note` 记录核验方式。
- 图片走受保护接口，不暴露 `uploads/` 静态路径。
- 不做用户模拟登录、SQL 控制台、批量 PII 导出。

## 11. Seed、CI、部署

- `ADMIN_USERNAME` / `ADMIN_PASSWORD` 环境变量；无默认密码。
- `seed_demo.py` 或 `seed_admin.py`；生产拒绝，`--reset` 需 `--yes`。
- 管理员恢复：不做 UI 自助；提供 server-side CLI（如 `uv run python scripts/reset_admin_password.py`，从 `backend/` 运行）或环境变量 re-seed，需服务器 shell 权限，操作以 `actor_user_id=NULL` + `actor_username='system'` 写日志/审计。
- 后端 `ruff` + `pytest` + OpenAPI `--check`；admin 前端独立 lint/typecheck/build。
- nginx `location /admin/` 用 `try_files $uri $uri/ /admin/index.html` 支持 history 路由；API 仍 `/api/v1`。
- 学生端构建与演示脚本不受影响。

## 12. 分期与验收

> 档位对应：Phase 0/1 = 11.29 必须；Phase 2 的密码申请审批 = 11.29 目标，其余 Phase 2（users 列表/详情只读、用户禁用/强制下线、任务重试/取消、内容隐藏/标记）= 演示后；Phase 3/4 = 演示后。
>
> 进度（2026-11-28）：Phase 0（ADM-002/009）已随 #123 合入；Phase 1 端点尚未实现；admin 前端页面在 PR #120（未合）。

| 阶段 | 内容 |
|---|---|
| Phase 0 | role/disabled/require_admin、admin 登录、audit 表、password_reset_requests 表、seed admin |
| Phase 1 | overview、system、tasks/ai-logs 只读、审计列表只读 |
| Phase 2 | 密码申请审批、users 列表/详情只读、用户禁用/强制下线、任务重试/取消、内容隐藏/标记 |
| Phase 3 | AI 成本/失败趋势、内容质量队列、导出、告警 |
| Phase 4 | 只读 auditor、保留策略、webhook、缓存清理、批量操作、IP 白名单 |

验收：

- 学生 token `/admin/*` 403 `ADMIN_REQUIRED`；admin token 200。
- 禁用用户旧 token 失效、登录被拒（403 `ACCOUNT_DISABLED`）。
- 总览数字与 DB 一致；AI 指标与 `ai_call_logs` 一致。
- 任务重试后学生任务中心状态一致。
- 密码申请：提交、去重、限流、审批、拒绝、24h、强制改密、旧会话失效。
- 临时密码不出现在日志/审计/数据库明文；只显示一次。
- 所有写操作有审计；审计写失败回滚。
- 列表分页/搜索可用；不返回敏感字段。
- 管理端构建进入 CI；学生端不受影响。

## 13. 默认值与已定项

1. admin token TTL 已实现 8h（ADM-002；学生仍为 7d）。
2. 审计保留天数（建议 180 天）。
3. 密码申请限流阈值（建议 3 次/天/IP+用户名）。
4. 是否给 `ai_call_logs` 加 `task_id` / `request_id`（建议加；`task_id` 优先 Phase 1）。
5. 告警阈值与通知渠道（MVP 页面告警）。
6. 内容审核字段已定：`questions.hidden_at`/`hidden_reason`/`flagged_at`/`flag_reason`（随 ADM-006 补迁移）；不用 `content_flags`。

## 14. 链接

- ADR-005：独立管理端。
- ADR-009：管理端进入 11.29 演示。
- `docs/agent/04-todos.md` §1.6：ADM 任务。
- `docs/agent/05-architecture.md` §6.10：Admin API 入口。
- `docs/agent/06-file-tree.md`：`admin/` 目录。
- `admin/README.md`：管理端目录说明。
