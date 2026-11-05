# admin · 内部运维台（P1 占位）

> 状态：P1 规划中，尚未开始业务代码。
> 决策：`docs/adr/ADR-005-admin-console.md`（2026-11-06，霹雳马桶 + 人机）。
> 重要：不进入 11.29 学生演示路径；不是教师端，也不是完整后台管理。

## 这个目录是什么

给两位开发者使用的内部运维台，用来：

1. 看系统总览：用户、错题、生成题、练习量、AI 成功率/延迟/失败任务。
2. 定位内容：错题/生成题列表与详情，软删除/隐藏明显有问题的内容。
3. 恢复任务：查看 `generation_task`，重试失败任务。
4. 查 AI 成本：`ai_call_logs` 的 operation/model/status/latency/tokens/error。

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
│   ├── router/           # /admin/login、/admin、/admin/users...
│   ├── stores/auth.ts    # 独立 localStorage key
│   ├── layouts/AdminShell.vue
│   ├── components/       # KPI card、DataTable、StatusTag...
│   └── views/            # Login/Dashboard/Users/Questions/Tasks/AiLogs
└── README.md
```

## 页面与优先级

| 页面 | 内容 | 优先级 |
|---|---|---|
| 登录 | 管理员账号登录；非 admin 拒绝 | P1 |
| 总览 | 4 个 KPI + AI 成功率/延迟 + 失败任务数 | P1 |
| 用户 | 列表、搜索、禁用/启用；不重置密码、不模拟登录 | P1 |
| 内容 | 错题/生成题列表与详情；软删除/隐藏 | P1 |
| 任务 | 队列列表、状态筛选、失败重试 | P1 |
| AI 日志 | operation/model/status/latency/tokens/error | P1 |
| 审计 | admin 删除/重试/禁用记录 | P2 |

## 后端依赖（尚未实现）

- `users.role`（student/admin）+ migration + seed 管理员。
- `require_admin` 依赖：查 DB 角色，学生 token 一律 403。
- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/users`、`PATCH /api/v1/admin/users/{id}`
- `GET /api/v1/admin/questions`、`DELETE /api/v1/admin/questions/{id}`
- `GET /api/v1/admin/tasks`、`POST /api/v1/admin/tasks/{id}/retry`
- `GET /api/v1/admin/ai-logs`

## 开始条件

1. 11.21 核心闭环稳定，P0 没有阻塞 bug。
2. ADR-005 已确认，`users.role` 契约写进 `05-architecture.md`。
3. 先做“登录 + 总览 + 用户只读”，不要一次做全。

## 安全底线

- 不提交默认管理员密码；seed 用环境变量或一次性密码。
- admin 响应不返回 `password_hash`、密钥、其他用户敏感信息。
- 所有删除软删；P2 审计日志。
- admin 不直接执行 SQL，不做用户模拟登录。
- admin 的 localStorage key 与学生端分开（如 `bababoi:admin-token`）。
