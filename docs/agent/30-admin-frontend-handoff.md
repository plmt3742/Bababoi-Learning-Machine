---
owner: 霹雳马桶
last_updated: 2026-11-28
status: active
read_when: 继续开发/验收 Admin 管理端前端，或接手当前会话时
---

# 30 · Admin 管理端前端交接（新会话入口）

> 先读：`docs/agent/00-context.md` → 本文 → `admin/README.md` → `admin/API_CONTRACT.md` → `docs/agent/29-admin-backend-handoff.md`。
> 当前结论：**前端代码完成并可本地演示；后端 ADM-002 地基已合（#123），只读端点 #124 待合；真实联调未完成。**

## 1. 项目现状

- 仓库：Bababoi-Learning-Machine（主分支 `main`；Admin 是独立应用）。
- Admin 独立应用：`admin/`，Vue 3 + Vite + TS + Arco Design Vue。
- Admin 设计语言：Calm Academic，浅色纸面、单一蓝色、表格优先；不要改回深色 ops 主题。
- 后端：FastAPI + SQLite/MySQL；学生端已有 auth/questions/tasks/practice/ai logs/stats/health。
- 后端 Admin API：ADM-002 地基已合（#123：角色/禁用/审计/管理员登录）；只读端点 #124 待合；`/api/v1/admin/system` 在 #124 合并前仍可能 404。

## 2. 已提交的 PR

- PR：#120
  https://github.com/plmt3742/Bababoi-Learning-Machine/pull/120
- 分支：`feat/admin-console-ui`
- Commit：`2c465da feat(admin): add API-driven management console`（本分支已合入最新 main）
- 状态：open，**未合并**
- CI：frontend ✅ / backend ✅ / migrations-mysql ✅（以 PR checks 为准）
- 变更：`admin/` 前端 + `admin/API_CONTRACT.md` + `docs/agent/29-admin-backend-handoff.md` + 本文档；不改学生端 `frontend/` 业务。
- 关联：#123（ADM-002 后端地基）、#124（admin 只读端点）、#125（admin 文档 review）。
- 合并前按仓库规则等用户确认；不要直接合 main。

PR 包含：

- `admin/` 完整前端
- `admin/API_CONTRACT.md`
- `docs/agent/29-admin-backend-handoff.md`
- `docs/agent/30-admin-frontend-handoff.md`
- 本地演示模式（默认关闭）

## 3. 现在怎么运行

### 3.1 管理端前端

```bash
cd "G:\AIworkspace\opencode\BababoiLearningMachine\admin"
pnpm install
pnpm dev
```

默认 dev：`http://127.0.0.1:5174/admin/login`
Vite 代理 `/api` 到 `http://127.0.0.1:8000`。

本地验证命令：

```bash
pnpm typecheck
pnpm build
```

### 3.2 当前已启动的预览

- 新前端（G 盘）：`http://127.0.0.1:5200/admin/login`
- 旧 mock 预览：`http://127.0.0.1:5183/admin/`
- 旧 mock 账号：`admin / admin123`（仅旧页面）

新前端的端口是临时的；重启后以 `pnpm dev` 输出为准。

### 3.3 演示模式

`admin/.env.local`（已被 gitignore）：

```env
VITE_ADMIN_DEMO=true
VITE_ADMIN_DEMO_USERNAME=admin
VITE_ADMIN_DEMO_PASSWORD=admin123
```

- 新前端演示账号：`admin / admin123`
- 演示模式会拦截 `/api/v1/admin/*`，返回内存数据；刷新页面即重置。
- 这不是真实后端；真实联调前必须关闭 `VITE_ADMIN_DEMO` 或删除 `.env.local`。
- `.env.example` 提供模板；默认 `VITE_ADMIN_DEMO=false`。

## 4. 前端实现内容

### 4.1 数据层

- `admin/src/api/client.ts`
  - `/api/v1` fetch 封装
  - Bearer `bababoi:admin-token`
  - 统一 `{detail:{code,message,request_id}}` 错误
  - 20 秒超时
  - 401 清理 token + 跳 `/admin/login`
  - `VITE_ADMIN_DEMO=true` 时进入本地 demo handler
- `admin/src/api/admin.ts`
  - admin auth、overview、users、password-requests、questions、tasks、ai-logs、audit、alerts、system 全部调用
- `admin/src/stores/adminData.ts`
  - users/passwordRequests/questions/tasks/aiLogs/auditLogs/alerts/overview/system
  - `loadAll()` + 各域 loader
  - `pendingPasswordCount` / `activeAlertCount` / `failedTaskCount` / `queuedTaskCount`
  - 写操作后刷新相关列表、overview、alerts
- `admin/src/stores/auth.ts`
  - 真实 `/admin/auth/login`、`/admin/me`、`/admin/logout`
  - 只接受 `role=admin`
  - 独立 token/user key
- `admin/src/mock/demo.ts`
  - 仅本地演示；模拟合同接口和操作
  - 数据不持久化

### 4.2 页面

- 登录
- 运营总览
- 用户管理（列表/详情/禁用/启用/强制下线）
- 密码申请（列表/通过/拒绝/重新生成临时密码）
- 内容管理（列表/详情/隐藏/恢复/标记/取消标记；生成题/任务/审计）
- 任务中心（列表/详情/时间线/重试/取消）
- AI 调用日志（列表/详情/原始输出门禁）
- 审计日志（列表/详情/before-after/CSV）
- 告警中心（列表/确认/取消确认/关联跳转）
- 系统健康（真实结构，按合同展示）

### 4.3 交互修复已完成

- 侧栏徽标不再硬编码，来自 store。
- 详情抽屉使用 `min(width, 100vw)`，≤760 全屏。
- 弹窗在窄屏使用视口宽度。
- 增加 `focus-visible`、`.adm-sr-only`。
- 登录去掉了假 `admin/admin123`，改为真实 API；demo 仅由 env 开关启用。
- 总览统计范围假控件已移除。
- 审计详情入口已可达。
- 密码审批展示提交邮箱 vs 注册邮箱，提交原因/渠道。
- AI raw 展开需要 reason，并提示写审计。

## 5. 后端进度与剩余

后端同学按以下两份材料继续：

- `admin/API_CONTRACT.md`：完整字段/示例
- `docs/agent/29-admin-backend-handoff.md`：数据库/权限/流程/验收

ADM-002（#123）已合：`users.role/disabled_at/...`、`require_admin`、管理员 seed、`/admin/auth/login`、`/admin/me`、`/admin/logout`、`admin_audit_logs`、`password_reset_requests` 基础表。以下按剩余项列出：

1. ✅ `users.role`、`disabled_at`、`disabled_reason`、`must_change_password`、`temp_password_expires_at`
2. ✅ `require_admin`（每次查 DB）
3. ✅ 管理员 seed（`scripts/seed_admin.py`，无默认密码）
4. ✅ `/api/v1/admin/auth/login`、`/admin/me`、`/admin/logout`
5. ✅ `admin_audit_logs`、`password_reset_requests`（基础表/登录审计）
6. ⏳ `questions` 审核字段：`hidden_at/hidden_reason/flagged_at/flag_reason`
7. ⏳ `/api/v1/admin/overview`
8. ⏳ `/api/v1/admin/users` + status/force-logout
9. ⏳ `/api/v1/admin/password-requests` + approve/reject/regenerate
10. ⏳ 公开 `POST /api/v1/auth/password-reset-requests`（固定 202 泛化响应）
11. ⏳ `/api/v1/admin/questions` + moderation
12. ⏳ `/api/v1/admin/tasks` + retry/cancel
13. ⏳ `/api/v1/admin/ai-logs` + raw
14. ⏳ `/api/v1/admin/audit` + detail + export.csv
15. ⏳ `/api/v1/admin/alerts` + ack/unack
16. ⏳ `/api/v1/admin/system`
17. ⏳ 学生端错题列表/详情过滤 `status='hidden'`

#124 是只读端点（概览/用户/任务/AI 日志/审计/系统）的落地单；写操作和内容审核随后继续。

关键约束：

- 审计与写操作同一事务；审计失败回滚。
- 临时密码只返回一次，不写日志/审计/数据库明文；24h 有效。
- 管理员重试/取消：failed 才能重试、queued 才能取消；running 不中断。
- 内容 hidden 对学生不可见；flagged 不改变可见性。
- 审计 CSV 要 UTF-8 BOM、中文表头、引号转义。
- 告警、侧栏、总览计数必须同源。
- 管理员账号不能公开注册，不能有默认密码。

## 6. 前端仍未处理好的点

这些不是后端接口问题，是前端/交互仍需做的：

1. **任务重试/取消**：目前直接执行，没有确认/撤销；取消后没有重新排队。
2. **告警确认**：没有撤销；确认后只改状态。
3. **通知铃铛**：仍是死按钮，没有面板/跳转。
4. **顶栏时钟**：`new Date()` 只在首次渲染计算，不会走。
5. **一次性临时密码**：结果页“我已记录，关闭”在没复制时也能点；复制失败无提示。
6. **390 表格**：详情/操作列仍可能在横向滚动末端；目前只修了抽屉和弹窗，表格未全面卡片化。
7. **分页**：列表一次拉 100 条，没有真正分页/加载更多。
8. **缺失聚合指标**：审计今日操作/敏感读取、密码平均处理时长、告警周统计/平均确认时长合同没有，页面显示 `—`。
9. **导出**：审计走后端 CSV；用户/AI 日志是前端从已加载数据生成，未写服务端审计。
10. **术语**：审计页仍有 `append-only`；任务阶段仍有“生题 · 第 N 段”。
11. **移动端操作**：行内按钮触控尺寸、操作列 sticky 仍需统一。
12. **前端测试/CI**：没有 admin lint、单测或 E2E；当前只有 typecheck/build + 本地浏览器 smoke；PR 的 CI 不构建 admin。

## 7. 设计评审的高优结论（避免丢）

之前 11 个审查单元覆盖 9 页 + 登录/壳层 + 7 个子界面。最重要的跨页问题：

- KPI/徽标/列表需单一数据源；任何操作后所有视图同步。
- 假控件要么接通要么删：统计范围、刷新、通知铃铛、用户下拉。
- 危险操作要“确认 → 执行中 → 结果 → 审计/撤销”：用户禁用/强制下线、内容隐藏/标记、任务取消/重试、告警确认。
- 详情闭环：审计详情可达；内容详情看得到生成题；告警可跳任务/申请；AI 日志可关联任务；用户详情看待审批密码申请。
- 390 抽屉/弹窗/表格必须可用。
- 状态词表、时间格式、ID 格式、tone 语义要统一。
- 对比度：`--adm-ink-3` 原色 3.4–3.6:1 不足；建议 #5b6577 / #66707f。
- 14px UI 下限在壳层/抽屉/告警行曾被打破；不要回到 10.5px。

## 8. 设计文档位置

- 产品/范围：`docs/agent/28-admin-console.md`
- 决策：`docs/adr/ADR-005-admin-console.md`、`docs/adr/ADR-009-admin-in-demo.md`、`docs/adr/ADR-010-scope-roles-types-subjects-stages.md`
- 后端交接：`docs/agent/29-admin-backend-handoff.md`
- 前端合同：`admin/API_CONTRACT.md`
- PR #120 是 Admin 前端实现；#125 是 admin 文档 review；#124 是 admin 只读端点。

## 9. 工作区/清理提醒

- Admin 的已跟踪版本在 `feat/admin-console-ui` / PR #120；主工作区里的 `admin/` 可能只是未跟踪副本，不要把它当第二个实现。
- 主工作区可能还有学生端/mascot 的未提交改动；不要为了这个 PR 盲目 `add/commit/clean`。
- 本地 `admin/node_modules`、`dist`、dev 日志不要提交；`.env.local` 已被 gitignore。
- 合并前确认 `admin/README.md` 与 main 的 admin 文档不冲突；本分支已合入最新 main。
- 本地预览端口以 `pnpm dev` 输出为准，不要把旧 mock 预览当真实后端验收。

## 10. 新会话建议的下一步

优先级从高到低：

1. 先合 #124 的 admin 只读端点，再把 `VITE_ADMIN_DEMO` 关掉做真登录/真数据联调；#123 已有管理员登录地基。
2. 继续前端 P1：任务/告警确认与撤销、密码关闭门禁、移动端表格操作、分页。
3. 增加 admin CI：`pnpm install && pnpm typecheck && pnpm build`，以及最小 Playwright smoke。
4. 清理本地临时 worktree/旧服务；合并前处理主工作区的 untracked `admin/` 副本。
5. 设计评审中的跨页修正（KPI 单一数据源、状态词表、对比度、术语）逐项落地。

## 11. 验证记录

- `cd admin && pnpm typecheck`：通过。
- `cd admin && pnpm build`：通过；仅 Vite/Arco bundle-size warning。
- 浏览器 smoke：演示登录、总览、用户列表、侧栏徽标、详情页可打开；浏览器控制台无应用错误。
- 后端 #123 已合管理员登录地基；只读端点 #124 待合，真实数据 E2E 仍未完成。
- PR #120 CI：frontend/backend/migrations 全绿（以 PR checks 为准）。

## 12. 一句话交接

**Admin 前端和 API 合同在 PR #120；后端 ADM-002 地基已合（#123），只读端点 #124 待合。不要合并/上线成“真实已完成”，也不要把 demo 数据当真实数据。**
