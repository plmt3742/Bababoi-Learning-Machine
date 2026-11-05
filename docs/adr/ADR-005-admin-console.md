# ADR-005: 独立 admin 管理端（P1 内部运维台）

- 状态：Accepted
- 日期：2026-11-06
- 决策人：霹雳马桶、人机
- 相关任务：ADM-001 ~ ADM-008
- 相关文档：`docs/agent/01-project.md`、`docs/agent/06-file-tree.md`、`docs/agent/04-todos.md`、`docs/adr/ADR-002-mvp-scope.md`

## 1. 背景

项目已有学生端 `frontend/` 与后端 `backend/`。两位开发者需要一个**内部运维台**来回答以下问题：

- 现在有多少用户、错题、生成题、练习记录？
- AI 分析/生题的成功率、延迟、token 成本如何？失败任务在哪里？
- 某道题/某道生成题内容有问题时，如何快速定位、隐藏或删除？
- 演示前数据是否完整？失败任务能否重试？

此前 `01-project.md` 与 ADR-002 明确把“完整后台管理”和“教师端”列为非目标。本次决策不是做完整后台，也不是教师端，而是**最小内部运维台**，用于两人开发和演示保障。

## 2. 决策

**创建独立的 `admin/` 前端应用，作为 P1 内部运维台；不进入 11.29 学生演示路径。**

### 2.1 范围（P1）

| 模块 | 能力 | 说明 |
|---|---|---|
| 登录/权限 | `users.role = student \| admin`；`require_admin`；学生 token 访问 `/admin/*` 返回 403 | 复用同一 JWT；后端每次查 DB 角色，不只信 token claim |
| 总览 | 用户数/错题数/生成题数/练习数；AI 成功率、平均延迟、失败任务数 | 只读 |
| 用户管理 | 列表、搜索、查看统计、禁用/启用 | P1 不做重置密码、不模拟登录 |
| 内容管理 | 错题/生成题列表与详情、软删除/隐藏、标记 bad output | P1 不做富文本编辑 |
| 任务/AI 运维 | `generation_task` 列表、失败重试；`ai_call_logs` 的 operation/model/status/latency/tokens/error | P1 只做查看 + 重试 |
| 审计日志 | 记录 admin 的删除/重试/禁用操作 | P2 |

### 2.2 明确不做

- 教师端、班级/作业/家校沟通。
- 完整 RBAC、多租户、组织架构。
- 付费、计费、发票。
- 用户模拟登录、直接改数据库、批量导出个人数据。
- 内容创作/富文本编辑器（学生端已有录入页）。

### 2.3 技术形态

```text
admin/                            # 独立 Vue 3 + Vite + TS + Arco app
├── package.json
├── vite.config.ts                # base: '/admin/'；dev 5174；代理 /api → :8000
├── index.html
├── .env.example
└── src/
    ├── main.ts / App.vue
    ├── api/                      # client、admin.ts、types.ts
    ├── router/                   # /admin/login、/admin、/admin/users...
    ├── stores/auth.ts            # 独立 localStorage key，避免与学生端互踢
    ├── layouts/AdminShell.vue    # 侧边栏 + 顶栏，表格优先
    └── views/                    # Dashboard/Users/Questions/Tasks/AiLogs
```

后端：

```text
backend/app/api/v1/admin/         # admin router，全部 require_admin
backend/app/services/admin_service.py
backend/app/schemas/admin.py
backend/app/core/deps.py          # require_admin
```

部署：nginx 增加 `location /admin/` 静态目录；`/api/` 仍反代到后端。CI 增加 admin 的 lint/typecheck/build job。

### 2.4 分期

| 时间 | 事项 |
|---|---|
| 11.6–11.7 | ADR-005 + `admin/README.md` 占位 + 文档同步；不写业务代码 |
| 11.8–11.14 | 不碰 admin，保核心纵向切片 + 部署 |
| 11.15–11.21 | 若核心闭环稳定：角色/migration → overview → admin 登录壳 + 总览/用户只读（约 2–3 天） |
| 11.22–11.29 | 冻结新功能；核心稳定才加任务重试/AI logs；否则只放 PPT 未来规划 |
| 11.29 后 | 内容审核、审计日志、导出、完整 RBAC |

### 2.5 验收

- 学生 token 访问所有 `/admin/*` 返回 403；admin token 返回 200。
- 总览数字与 DB 一致；列表分页、搜索可用。
- 失败任务可从 admin 重试；重试后任务中心状态一致。
- 响应不返回 `password_hash`、密钥、其他用户敏感信息。
- admin 构建进入 CI；学生端构建与 11.29 演示脚本不受影响。
- 无默认管理员密码；seed 管理员使用环境变量或一次性密码。

## 3. 后果

### 正面

- 两位开发者有统一的排障入口，减少查库/翻日志成本。
- 答辩时可展示 AI 成功率、延迟、队列与成本，支撑“工程质量”叙事。
- 与教师端解耦，未来做教师端时不需要重做权限模型。

### 负面/代价

- 多一个前端应用、一个 CI job、一个部署路径；对 2 人团队是额外维护成本。
- 增加 `users.role`、admin API、`require_admin` 与 migration；属于跨模块改动。
- 如果排进 M1/M2 的 P0，会挤占核心闭环时间；因此严格限定 P1，不进入 11.29 演示。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 范围蔓延成完整后台 | 本 ADR 明确只做 5 个模块；新增模块必须删一个同等工作量 P1 |
| admin 权限绕过 | `require_admin` 查 DB 角色；所有 admin 路由统一依赖；测试 401/403 |
| 多一个应用拖慢交付 | 11.21 前只落 ADR + 占位；核心未稳不写业务代码 |
| 误删数据 | 所有删除软删；P2 审计日志；不做直接 SQL 编辑 |
| 学生端/管理端 session 互踢 | admin 使用独立 localStorage key 与独立登录页 |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| 管理页放进 `frontend/src/views/admin/` | 成本最低，构建/部署不变 | 与学生端共享路由/包体/登录态，权限边界模糊；不是独立文件夹 | 用户明确要求独立 `admin/` |
| 完整后台管理（用户/内容/统计/运营） | 功能全 | 25 天不可行，挤占 P0 | 违反范围约束 |
| 只做种子脚本 + 查库 | 零前端成本 | 演示/排障体验差，无法展示 AI 质量 | 不能支撑答辩叙事 |
| 做教师端 | 产品想象空间大 | 用户/场景未验证，范围过大 | 教师端仍为 P2 |

## 5. 链接

- 范围：`docs/agent/01-project.md` §5
- 目录：`docs/agent/06-file-tree.md`
- 任务：`docs/agent/04-todos.md` §1.6
- MVP 范围：`docs/adr/ADR-002-mvp-scope.md`
- 管理端占位：`admin/README.md`
