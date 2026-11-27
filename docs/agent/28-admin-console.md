---
owner: 霹雳马桶
last_updated: 2026-11-27
status: active
read_when: 开发/联调 admin 管理端前；评审监控、审计、密码重置时
---

# 28 · Admin 管理端规划与后端对接

> 决策：ADR-005（独立管理端）+ ADR-009（进入 11.29 演示）。  
> 前端：独立 `admin/` 应用；后端：`/api/v1/admin/*`，全部 `require_admin`。  
> 本文是管理端的详细方案与后端对接单；代码实现以本文和 OpenAPI 为准。

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
| 必须 | 管理员登录/403 边界、总览、任务列表/详情、AI 调用日志、审计列表、系统健康 |
| 目标 | 线上密码申请 + 管理员审批 + 临时密码 24h + 学生强制改密 |
| 演示后 | 内容标记/质量队列、导出、告警中心、批量操作、只读 auditor、完整审计保留策略 |

> 若密码申请的后端基础（role/audit/request）在演示前未完成，只在 PPT 中讲流程，不在现场演示写操作。

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

## 3. 信息架构

### 3.1 管理端页面

| 页面 | 路径 | 内容 |
|---|---|---|
| 登录 | `/admin/login` | 管理员登录；非 admin 403 |
| 总览 | `/admin` | 业务/AI/任务/内容/系统健康 |
| 用户 | `/admin/users` | 列表、搜索、禁用/启用、详情 |
| 密码申请 | `/admin/password-requests` | 待审批、通过、拒绝、审计 |
| 内容 | `/admin/questions` | 错题/生成题列表、详情、软删/隐藏/标记 |
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
- 任务详情：时间线、错误、关联题目、AI 调用、raw 入口。
- 操作：失败重试、排队取消；running 不强行中断；管理员重试绕过 owner 校验但校验状态并写审计。
- AI 日志：operation/model/status/latency/tokens/key_source/error；列表不返回 raw。
- raw 输出：单独接口，截断 8k，访问写审计。
- 成本：token × 模型单价估算；标注“估算”，不做真实计费。
- 识图缓存：MVP 只读统计；P2 再考虑清理。

### 4.3 用户

- 列表：用户名、邮箱（脱敏）、角色、状态、错题/生成题/练习数、最近登录。
- 详情：账号资料、统计、最近任务、AI 设置状态（provider/model/key_last4，不显示 Key）。
- 操作：禁用/启用、强制下线、密码申请审批。
- 禁用：`disabled_at` + `token_version += 1`；旧 token 失效；登录拒绝。
- 禁止禁用自己、禁止禁用最后一个 active admin。

### 4.4 内容

- 错题列表：题干摘要、用户、学科、题型、掌握状态、标记/软删、时间。
- 错题详情：全文、选项/空位、答案/解析、AI 分析、生成题、图片、练习次数、任务历史。
- 生成题：父题、target_index、难度、validation_status/score、model/prompt_version、标记。
- 操作：软删除/恢复、隐藏、标记 bad output；不做富文本编辑。
- 图片：受保护接口，不暴露 `uploads/` 静态路径；查看写审计。
- 质量队列：invalid/fallback/低分/被标记；P1 建表，P2 完整工作流。

### 4.5 系统

- 健康：`/health`、`/ready`、DB、LLM 模式、worker、版本/环境、上传目录磁盘占用。
- 配置：只读展示任务并发、重试上限、硬超时、图片限制、分页上限、BYOK 是否启用。
- 配置变更走部署/环境变量，不在 admin UI 直接改 `.env`。
- 演示 seed 状态可展示；重置演示数据只走脚本，不放进 UI。

## 5. 线上密码重置（定稿）

### 5.1 流程

1. 学生登录页点“忘记密码”，进入 `/forgot-password`。
2. 填写：`username`、注册邮箱（可选）、申请原因。
3. 后端校验用户名存在；同一用户已有 pending 申请则拒绝；按 IP/用户名限流。
4. 创建 `password_reset_requests`，状态 `pending`。
5. 管理员在 `/admin/password-requests` 核对用户名/邮箱/账号状态；填写核验说明和原因。
6. 通过后：生成临时密码、bcrypt 入库、`must_change_password=true`、`temp_password_expires_at=now+24h`、`token_version += 1`、写审计。
7. 管理端弹窗只显示一次临时密码；管理员通过外部渠道通知学生。
8. 学生用临时密码登录；登录响应 `must_change_password=true`。
9. 前端强制跳转设置页改密；后端 `require_password_ready` 拦截其他业务接口。
10. 学生用临时密码 + 新密码改密；清标记/过期时间、`token_version += 1`、审计；当前登录退出，用新密码重新登录。

### 5.2 边界

- 不做学生状态查询页、不做自助领取临时密码、不做邮件/短信。
- 临时密码由后端生成（12 位左右，去除易混淆字符），只在审批响应返回一次；`Cache-Control: no-store`。
- 不写日志/审计/数据库明文；管理端不持久化；关闭弹窗即清空。
- 临时密码 24h 有效；过期后登录和业务接口都拒绝，学生重新申请。
- 管理员忘记临时密码只能重新生成；旧临时密码立即失效。
- 目标为管理员/自己/禁用账号时不允许重置。
- 审计与重置同一事务；审计写失败则回滚，不生成临时密码。

### 5.3 接口

```http
POST /api/v1/auth/password-reset-requests
{ "username": "student01", "email": "student01@example.com", "reason": "忘记密码" }
```

```http
GET  /api/v1/admin/password-reset-requests?status=pending
GET  /api/v1/admin/password-reset-requests/{id}
POST /api/v1/admin/password-reset-requests/{id}/approve
POST /api/v1/admin/password-reset-requests/{id}/reject
```

通过响应（只返回一次）：

```json
{
  "temporary_password": "K7m2P9q4R6s8",
  "must_change_password": true,
  "temp_password_expires_at": "2026-11-28T12:00:00Z",
  "audit_id": 123
}
```

## 6. 数据模型

### 6.1 `users` 新增字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | VARCHAR(16) NOT NULL DEFAULT 'student' | student/admin |
| `disabled_at` | DATETIME NULL | 禁用时间 |
| `must_change_password` | BOOLEAN NOT NULL DEFAULT false | 临时密码强制改密 |
| `temp_password_expires_at` | DATETIME NULL | 24h 有效期 |
| `password_changed_at` | DATETIME NULL | 最近改密时间 |

**不新增姓名/学号。**

### 6.2 `password_reset_requests`

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `user_id` | 命中的学生 ID；用户名不存在时为空 |
| `username` | 提交的用户名 |
| `submitted_email` | 提交的邮箱（可选） |
| `reason` | 申请原因 |
| `status` | pending/approved/rejected |
| `reviewed_by` / `reviewed_at` | 审批管理员/时间 |
| `review_note` | 审批备注/拒绝原因 |
| `created_at` | 申请时间 |
| `ip` / `user_agent` | 申请来源 |

索引：`(status, created_at)`、`(user_id, created_at)`。不存临时密码、secret、明文密码。

### 6.3 `admin_audit_logs`

| 字段 | 说明 |
|---|---|
| `actor_user_id` / `actor_username` | 管理员及快照 |
| `action` | user.disable / task.retry / password_request.approve / ai_log.view_raw 等 |
| `target_type` / `target_id` / `target_label` | 目标及快照 |
| `target_owner_id` | 内容所属学生 |
| `before_json` / `after_json` | 脱敏 diff |
| `reason` | 必填原因 |
| `result` | success/failed |
| `request_id` / `ip` / `user_agent` | 来源 |
| `created_at` | 时间 |

索引：`(actor_user_id, created_at)`、`(action, created_at)`、`(target_type, target_id)`。

### 6.4 其他建议

- `content_flags`：target_type/target_id/reason/severity/status/created_by/resolved_at（P1 建表）。
- `ai_call_logs.task_id`（P1）、`ai_call_logs.request_id`（P2）。
- `generation_task`：`(user_id, created_at)`、`(stage, status, created_at)`、`(error_code, created_at)`。
- `ai_call_logs`：`(created_at)`、`(status, created_at)`、`(operation, created_at)`。

## 7. API 总表

| 模块 | 端点 |
|---|---|
| 认证 | `POST /admin/auth/login`、`GET /admin/me` |
| 监控 | `GET /admin/overview`、`GET /admin/metrics/ai`、`GET /admin/metrics/tasks`、`GET /admin/health` |
| 用户 | `GET /admin/users`、`GET /admin/users/{id}`、`PATCH /admin/users/{id}`、`POST /admin/users/{id}/force-logout` |
| 密码申请 | `GET /admin/password-reset-requests`、`GET /admin/password-reset-requests/{id}`、`POST .../approve`、`POST .../reject`；公开 `POST /auth/password-reset-requests` |
| 内容 | `GET/DELETE /admin/questions/{id}`、`GET /admin/questions`、`POST /admin/questions/{id}/restore`、`POST /admin/questions/{id}/flag`、`GET /admin/generated-questions` |
| 任务 | `GET /admin/tasks`、`GET /admin/tasks/{id}`、`POST /admin/tasks/{id}/retry`、`POST /admin/tasks/{id}/cancel` |
| AI 日志 | `GET /admin/ai-logs`、`GET /admin/ai-logs/{id}`、`GET /admin/ai-logs/{id}/raw`、`GET /admin/ai-logs/export` |
| 审计 | `GET /admin/audit`、`GET /admin/audit/{id}`、`GET /admin/audit/export` |
| 系统 | `GET /admin/system` |

统一：`/api/v1` 前缀、Bearer JWT、`{items,total,page,page_size}`、统一错误信封、`X-Request-ID`。写操作带 `reason`，响应带 `audit_id`。

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

覆盖：admin 登录/失败/登出、用户禁用/启用/强制下线、密码申请通过/拒绝、任务重试/取消、内容软删/恢复/标记、raw/图片访问、审计导出、配置变更。

- 高风险写操作与审计同一事务；审计失败回滚。
- 现有 service 内部 commit 的，admin 侧需要 `commit=False` 或抽出不提交的内部函数。
- 审计不记录临时密码、secret、密码散列、API Key。
- 审计日志不提供 UI 删除；保留策略只走数据库任务。

## 10. 安全与隐私

- 管理端独立 token key/登录页；学生 token 403。
- 管理端登录限流；CORS 增加 `http://localhost:5174`，生产同源。
- 响应不返回 `password_hash`、JWT、API Key 密文、完整 Key。
- 邮箱列表脱敏；原始 AI/图片访问审计；导出脱敏、限行数。
- 图片走受保护接口，不暴露 `uploads/` 静态路径。
- 不做用户模拟登录、SQL 控制台、批量 PII 导出。

## 11. Seed、CI、部署

- `ADMIN_USERNAME` / `ADMIN_PASSWORD` 环境变量；无默认密码。
- `seed_demo.py` 或 `seed_admin.py`；生产拒绝，`--reset` 需 `--yes`。
- 后端 `ruff` + `pytest` + OpenAPI `--check`；admin 前端独立 lint/typecheck/build。
- nginx `location /admin/`；API 仍 `/api/v1`。
- 学生端构建与演示脚本不受影响。

## 12. 分期与验收

| 阶段 | 内容 |
|---|---|
| Phase 0 | role/disabled/require_admin、admin 登录、audit 表、password_reset_requests 表、seed admin |
| Phase 1 | overview、health、tasks/ai-logs 只读、users 只读 |
| Phase 2 | 密码申请审批、用户禁用/强制下线、任务重试/取消、内容软删/标记、审计列表 |
| Phase 3 | AI 成本/失败趋势、内容质量队列、导出、告警 |
| Phase 4 | 只读 auditor、保留策略、webhook、缓存清理、批量操作、IP 白名单 |

验收：

- 学生 token `/admin/*` 403；admin token 200。
- 禁用用户旧 token 失效、登录被拒。
- 总览数字与 DB 一致；AI 指标与 `ai_call_logs` 一致。
- 任务重试后学生任务中心状态一致。
- 密码申请：提交、去重、限流、审批、拒绝、24h、强制改密、旧会话失效。
- 临时密码不出现在日志/审计/数据库明文；只显示一次。
- 所有写操作有审计；审计写失败回滚。
- 列表分页/搜索可用；不返回敏感字段。
- 管理端构建进入 CI；学生端不受影响。

## 13. 待后端确认的默认值

1. admin token TTL（建议 8h）。
2. 审计保留天数（建议 180 天）。
3. 密码申请限流阈值（建议 3 次/天/IP+用户名）。
4. 是否给 `ai_call_logs` 加 `task_id` / `request_id`（建议加）。
5. 告警阈值与通知渠道（MVP 页面告警）。
6. `content_flags` 是否 Phase 1 建表（建议建表，Phase 2 使用）。

## 14. 链接

- ADR-005：独立管理端。
- ADR-009：管理端进入 11.29 演示。
- `docs/agent/04-todos.md` §1.6：ADM 任务。
- `docs/agent/05-architecture.md` §6.10：Admin API 入口。
- `docs/agent/06-file-tree.md`：`admin/` 目录。
- `admin/README.md`：管理端目录说明。
