# admin · 内部运维台（11.29 演示，占位）

> 状态：主分支仍为占位；ADM-002+ 在独立分支进行中，未并入 main。
> 决策：`docs/adr/ADR-005-admin-console.md` + `docs/adr/ADR-009-admin-in-demo.md`。
> 重要：管理端**进入 11.29 演示**，但演示只展示已实现能力；完整方案见 `docs/agent/28-admin-console.md`。不是教师端，也不是完整后台管理。

## 这个目录是什么

给两位开发者使用的内部运维台，用来：

1. 看系统总览：用户、错题、生成题、练习量、AI 成功率/延迟/失败任务。
2. 定位内容：错题/生成题列表与详情，软删除/隐藏明显有问题的内容。
3. 恢复任务：查看 `generation_task`，重试失败任务。
4. 查 AI 成本：`ai_call_logs` 的 operation/model/status/latency/tokens/error。
5. 处理密码申请：学生线上提交，管理员审批，临时密码只在管理端显示一次。

学生端仍在 `frontend/`；两者共用同一套后端 API，但 admin 使用独立的 `/api/v1/admin/*` 路由和 `require_admin` 权限。

## 计划中的结构

```text
admin/
├── package.json
├── vite.config.ts        # base: '/admin/'；dev 5174；代理 /api → :8000
├── index.html
├── .env.example
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── api/              # client、admin.ts、types.ts
│   ├── router/           # route path：/login、/、/users...（base=/admin/，实际 URL 为 /admin/login）
│   ├── stores/auth.ts    # 独立 localStorage key（bababoi:admin-token）
│   ├── layouts/AdminShell.vue
│   ├── components/       # KPI card、DataTable、StatusTag、ConfirmWithReason...
│   └── views/            # Login/Dashboard/Users/PasswordRequests/Questions/Tasks/AiLogs/Audit/System
└── README.md
```

## 页面与演示档位

| 页面 | 内容 | 演示档位 |
|---|---|---|
| 登录 | 管理员账号登录；非 admin 拒绝 | 必须 |
| 总览 | 4 个 KPI + AI 成功率/延迟 + 失败任务数 | 必须 |
| 用户 | 列表、搜索、禁用/启用、强制下线 | 演示后 |
| 密码申请 | 线上申请列表、审批/拒绝、临时密码一次性展示与重新生成 | 目标 |
| 内容 | 错题/生成题列表与详情；软删除/隐藏/标记 | 演示后 |
| 任务 | 队列列表、状态筛选、失败重试/排队取消 | 必须（列表/详情只读）/演示后（重试/取消） |
| AI 日志 | operation/model/status/latency/tokens/error；raw 单独接口 | 必须 |
| 审计 | admin 删除/重试/禁用/审批/敏感读取记录 | 必须（列表） |
| 系统 | 健康、版本/环境、只读配置 | 必须 |

> 必须档只读；密码申请是目标；用户管理、任务重试/取消、内容操作演示后。

## 后端依赖（尚未实现）

- `users.role`（student/admin）、`users.disabled_at`、`users.must_change_password`、`users.temp_password_expires_at` + migration + seed 管理员。
- `require_admin` 依赖：查 DB 角色，学生 token 一律 403。
- `admin_audit_logs` + 审计服务。
- `password_reset_requests` + 学生线上申请 + 管理员审批接口。
- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/users`、`PATCH /api/v1/admin/users/{id}`、`POST /api/v1/admin/users/{id}/force-logout`
- `GET /api/v1/admin/password-reset-requests`、`POST .../{id}/approve`、`POST .../{id}/reject`、`POST .../{id}/regenerate-temp-password`
- `GET /api/v1/admin/audit`
- `GET /api/v1/admin/questions`、`DELETE /api/v1/admin/questions/{id}`
- `GET /api/v1/admin/tasks`、`POST /api/v1/admin/tasks/{id}/retry`
- `GET /api/v1/admin/ai-logs`

## 开始条件

1. ADR-005 + ADR-009 已确认，`28-admin-console.md` 作为详细契约。
2. Phase 0 基础：`users.role`/`disabled_at`、`require_admin`、`admin_audit_logs`、seed admin。
3. 先做“登录 + 总览 + 任务/AI 日志只读”，再做密码申请审批等写操作。

## 安全底线

- 不提交默认管理员密码；seed 用环境变量或一次性密码。
- admin 响应不返回 `password_hash`、密钥、其他用户敏感信息。
- 所有删除软删；审计列表为演示必须，导出演示后；不提供 UI 删除。
- admin 不直接执行 SQL，不做用户模拟登录。
- admin 的 localStorage key 与学生端分开（如 `bababoi:admin-token`）。
- 不新增姓名/学号；密码申请只使用用户名 + 可选邮箱 + 原因。
- 临时密码只在管理端显示一次，24h 有效，学生登录后强制改密；不写日志/审计/数据库明文。
- 没有邮件/短信通知；管理员通过现有外部渠道通知学生。
