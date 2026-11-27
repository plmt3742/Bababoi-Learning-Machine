# admin · 内部运维台

> 状态：前端已完成真实 API 接线；后端 `/api/v1/admin/*` 仍待后端同学实现。
> 决策：`docs/adr/ADR-005-admin-console.md` + ADR-009。
> 重要：默认没有管理员账号；真实登录依赖后端初始化管理员。本地演示模式可用 `admin / admin123`，仅用于看页面。

## 当前状态

- 前端是独立 Vue 3 + Vite + TS + Arco 应用，保留 Calm Academic 视觉。
- 所有页面已从 mock 数据切到真实 API 层；`src/mock/data.ts` 已删除。
- 管理员登录、总览、用户、密码申请、内容、任务、AI 日志、审计、告警、系统健康均已接线。
- 真实后端尚未提供 `/api/v1/admin/*`；关闭演示模式后登录会返回 404，这是后端未实现，不是前端假数据回退。
- 本地演示模式会拦截 `/api/v1/admin/*`，可直接看完整页面；数据只在内存里，刷新会重置。
- 前端 `pnpm typecheck` 与 `pnpm build` 通过；真实接口联调待后端完成后进行。

## 启动

```bash
cd admin
pnpm install
pnpm dev
```

开发地址：`http://127.0.0.1:5174/admin/login`。
Vite 已代理 `/api` 到 `http://127.0.0.1:8000`。

```bash
pnpm typecheck
pnpm build
```

## 管理员账号

没有内置账号，也没有默认密码。后端需要：

1. 增加 `users.role = student | admin`，并初始化一个 `admin` 账号。
2. 实现 `POST /api/v1/admin/auth/login`、`GET /api/v1/admin/me`。
3. 所有 `/api/v1/admin/*` 使用 `require_admin`，学生 token 返回 403。

管理员账号由服务端环境变量或 seed 脚本创建；前端不保存、不显示默认密码。

### 本地演示模式

```bash
cp .env.example .env.local
# 编辑 .env.local：VITE_ADMIN_DEMO=true
pnpm dev
```

账号：`admin` / `admin123`。该模式只用于本地看页面，数据不持久化；生产构建必须保持 `VITE_ADMIN_DEMO=false` 或删除 `.env.local`。

## 后端合同

完整实现合同：[`API_CONTRACT.md`](./API_CONTRACT.md)

后端同学交接单：[`../docs/agent/29-admin-backend-handoff.md`](../docs/agent/29-admin-backend-handoff.md)

产品/范围定稿：`origin/docs/admin-console-plan` 分支的 `docs/agent/28-admin-console.md` 与 `docs/adr/ADR-009-admin-in-demo.md`。

核心端点：

```text
POST /api/v1/admin/auth/login
GET  /api/v1/admin/me
POST /api/v1/admin/logout
GET  /api/v1/admin/overview
GET  /api/v1/admin/users
GET  /api/v1/admin/users/{id}
POST /api/v1/admin/users/{id}/status
POST /api/v1/admin/users/{id}/force-logout
GET  /api/v1/admin/password-requests
POST /api/v1/admin/password-requests/{id}/approve
POST /api/v1/admin/password-requests/{id}/reject
POST /api/v1/admin/password-requests/{id}/regenerate-temp-password
POST /api/v1/auth/password-reset-requests
GET  /api/v1/admin/questions
GET  /api/v1/admin/questions/{id}
POST /api/v1/admin/questions/{id}/moderation
GET  /api/v1/admin/tasks
GET  /api/v1/admin/tasks/{id}
POST /api/v1/admin/tasks/{id}/retry
POST /api/v1/admin/tasks/{id}/cancel
GET  /api/v1/admin/ai-logs
GET  /api/v1/admin/ai-logs/{id}
POST /api/v1/admin/ai-logs/{id}/raw
GET  /api/v1/admin/audit
GET  /api/v1/admin/audit/{id}
GET  /api/v1/admin/audit/export.csv
GET  /api/v1/admin/alerts
POST /api/v1/admin/alerts/{key}/ack
POST /api/v1/admin/alerts/{key}/unack
GET  /api/v1/admin/system
```

## 结构

```text
admin/
├── src/api/          # client.ts + 全部 admin API 函数
├── src/stores/       # auth.ts + adminData.ts
├── src/layouts/      # AdminShell
├── src/components/   # KPI / 状态标签 / 审批弹窗 / 趋势图
├── src/views/        # 10 个页面
├── src/styles/       # admin.css + Calm Academic 对齐样式
└── API_CONTRACT.md   # 后端实现合同
```

## 安全边界

- 管理端使用独立 `bababoi:admin-token` / `bababoi:admin-user`，与学生端 localStorage 分开。
- 不返回 `password_hash`、API Key 密文、完整 Key 或临时密码。
- 原始 AI 输出需要单独请求并写审计。
- 所有管理员写操作由后端写审计；前端不做本地伪造。

## 已知未完成

- 后端 admin 路由、`users.role`、审计表、密码申请表未实现（由后端同学负责）。
- 真实登录与真实数据端到端联调未执行。
- 部分后端合同没有的聚合指标在页面上显示 `—`，不编造数字。
