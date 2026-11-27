# Admin real API contract (implementation contract)

Scope: real admin system. Backend prefix `/api/v1`, all `/admin/*` require an admin JWT.
Source of truth for product rules: `docs/agent/28-admin-console.md` (branch `origin/docs/admin-console-plan`) and `docs/adr/ADR-009-admin-in-demo.md`.

This file is an implementation contract for the backend and admin frontend. It is intentionally
close to the existing admin view data shapes so the current Calm Academic UI can stay.

## Conventions

- Auth: `Authorization: Bearer <jwt>`; the JWT is the existing student auth token with
  `users.role = 'admin'` checked against DB on every `/admin/*` request.
- Errors: existing `{"detail":{"code","message","request_id"}}` envelope.
- All list endpoints: `?page=1&page_size=20&q=&status=` and return
  `{"items":[...],"total":N,"page":1,"page_size":20}`.
- Display timestamps in UTC+8, e.g. `11-28 01:20` or `11-28 01:20:00` for task/audit rows.
  Keep raw ISO values only when needed (`raw_created_at`, etc.).
- Counts are integers (no leading zero strings). The frontend decides display.
- No `password_hash`, full API key, JWT, or temporary password in logs/audit.

## 1. Auth

### POST `/api/v1/admin/auth/login`

Body `{"username":"admin","password":"..."}`.
Uses the same login limiter as student login; if user is not admin or is disabled -> 403.
Writes `admin.login` audit on success.

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "must_change_password": false
  }
}
```

### GET `/api/v1/admin/me`

Returns the same `user` object. 401 if invalid/expired; 403 if not admin/disabled.

### POST `/api/v1/admin/logout`

204; writes `admin.logout` audit (best-effort). Client clears its own token.

### POST `/api/v1/auth/password-reset-requests` (public)

Body `{"username":"student01","email":"student01@example.com","reason":"忘记密码"}`.
Always `202 {"message":"如果账号存在，申请已提交"}`; do not reveal whether the account exists.
If username exists and there is no pending request, create a `password_reset_requests` row.
Do not create requests for admin accounts.

## 2. Overview

### GET `/api/v1/admin/overview`

```json
{
  "generated_at": "11-28 01:20:00",
  "stats": {
    "users": {"total": 2, "active": 2, "disabled": 0, "new_7d": 2},
    "content": {"questions": 12, "generated": 36, "practice": 45, "flagged": 1, "hidden": 0},
    "ai": {"calls_24h": 10, "success_rate": 97.2, "error_rate": 1.8, "invalid_rate": 1.0,
           "p50_latency_ms": 18400, "p95_latency_ms": 41200,
           "input_tokens": 1200000, "output_tokens": 220000, "estimated_cost": 12.84},
    "tasks": {"queued": 0, "running": 0, "failed": 1, "done_24h": 3, "canceled_24h": 0,
              "oldest_queue_seconds": 0},
    "password_requests": {"pending": 1, "approved_today": 0, "rejected_today": 0}
  },
  "failed_tasks": [TaskDTO],
  "pending_password_requests": [PasswordRequestDTO],
  "recent_audit": [AuditDTO],
  "alerts": [AlertDTO],
  "trend": {
    "success": [{"label":"11-22","value":96.8}],
    "latency": [{"label":"11-22","value":34.2}]
  }
}
```

`estimated_cost` may be `null` if no price is configured; frontend displays `—`.
Trends may be empty arrays on a fresh DB.

## 3. Users

### GET `/api/v1/admin/users`

Query: `q` (username/email), `status=active|disabled|all`, `page`, `page_size`.
Only `role='student'` users are returned. Disabled users remain visible.

`UserDTO`:

```json
{
  "id": 1,
  "username": "student01",
  "email": "student01@example.com",
  "status": "active",
  "role": "student",
  "questions": 12,
  "generated": 34,
  "practice": 41,
  "lastLogin": "11-27 21:14",
  "createdAt": "10-20 16:00",
  "hasPersonalKey": false,
  "provider": null,
  "model": null,
  "keyLast4": null,
  "pendingPasswordRequests": 0,
  "disabledAt": null,
  "disabledReason": null
}
```

`provider/model/keyLast4` come from `user_ai_settings`; never return the ciphertext.

### GET `/api/v1/admin/users/{id}`

`UserDTO` plus `recentTasks: TaskDTO[]` (max 3) and `passwordRequests: PasswordRequestDTO[]`
(most recent 3, all statuses).

### POST `/api/v1/admin/users/{id}/status`

Body `{"status":"disabled","reason":"..."}` or `{"status":"active"}`.
- reason required when disabling, min 4 chars.
- Cannot disable the last active admin; student list only, but enforce at service layer.
- Disabling sets `disabled_at`, `disabled_reason`, inactivates sessions by incrementing
  `token_version`; enabling clears disabled fields (does not restore old sessions).
- Audit in the same transaction; return `{user: UserDTO, audit_id: 123}`.

### POST `/api/v1/admin/users/{id}/force-logout`

Increments `token_version`; audit; returns `{"status":"ok","audit_id":123}`.

## 4. Password reset requests

### GET `/api/v1/admin/password-requests`

Query `status=pending|approved|rejected|all`, `q`, `page`, `page_size`.

`PasswordRequestDTO`:

```json
{
  "id": 301,
  "username": "student03",
  "email": "student03@example.com",
  "registeredEmail": "student03@example.com",
  "emailMatches": true,
  "accountStatus": "active",
  "reason": "忘记密码",
  "status": "pending",
  "submittedAt": "11-27 22:48",
  "reviewedBy": null,
  "reviewedAt": null,
  "reviewNote": null,
  "ip": "10.0.3.12",
  "expiresAt": null,
  "deliveryChannel": null,
  "mustChangePassword": false
}
```

`email` is the submitted email; `registeredEmail` is from the user row. Do not return a
temporary password or password hash here.

### POST `/api/v1/admin/password-requests/{id}/approve`

Body `{"reason":"...","verified":true,"delivery_channel":"wechat"}`.
- only pending; reason >= 4 chars; verified must be true.
- target must not be admin, must exist, must not be disabled.
- generate a 12-char temporary password, hash it into `users.password_hash`, set
  `must_change_password=true`, `temp_password_expires_at=now+24h`, increment `token_version`.
- request -> approved, reviewed_by/reviewed_at/review_note/delivery_channel/expires_at.
- write audit in the same transaction.

Response:

```json
{
  "request": PasswordRequestDTO,
  "temporary_password": "K7m2P9q4R6s8",
  "must_change_password": true,
  "expires_at": "11-28 22:48",
  "audit_id": 123
}
```

Set `Cache-Control: no-store`. Never store the plaintext.

### POST `/api/v1/admin/password-requests/{id}/reject`

Body `{"reason":"..."}`; only pending; reason >= 4 chars; sets rejected + review fields;
audit. Returns `{request: PasswordRequestDTO, audit_id: 123}`.

### POST `/api/v1/admin/password-requests/{id}/regenerate-temp-password`

Pending or approved, same generation rules; invalidates the previous temporary password.
Returns the same shape as approve. This is optional for the first frontend pass, but implement
the endpoint because the design needs recovery.

## 5. Questions

### GET `/api/v1/admin/questions`

Query `q` (id/excerpt/username), `status=active|hidden|all`, `flagged=true|false`, page.
List `QuestionDTO` can omit heavy detail arrays; it must include:

```json
{
  "id": 1042,
  "excerpt": "求函数 ...",
  "username": "student01",
  "subject": "高等数学",
  "chapter": "导数与极值",
  "type": "solve",
  "status": "active",
  "flagged": false,
  "flagReason": null,
  "createdAt": "11-27 21:08",
  "generated": 3,
  "practice": 8,
  "analysis": "考点：导数与极值；难度：中等。...",
  "hasImage": false
}
```

`status` is `active` when `questions.status='confirmed'` and `hidden` when
`questions.status='hidden'`. `flagged` is the quality flag, independent of visibility.

### GET `/api/v1/admin/questions/{id}`

Adds `contentMd`, `answerMd`, `explanationMd`, `sourceType`, `options`, `blanks`, `tags`,
`imagePath`, `generatedQuestions`:
`[{id,contentMd,answerMd,explanationMd,questionType,difficulty,targetIndex,validationStatus,
validationScore,model,promptVersion}]`, `tasks: TaskDTO[]`, `recentAudit: AuditDTO[]`.

### POST `/api/v1/admin/questions/{id}/moderation`

Body one of:
`{"hidden":true,"reason":"..."}`, `{"hidden":false}`, `{"flagged":true,"reason":"..."}`,
`{"flagged":false}`.
- hiding sets `status='hidden'`, `hidden_at`, `hidden_reason`; restoring sets
  `status='confirmed'` and clears hidden fields.
- flagging sets `flagged_at`, `flag_reason`; unflagging clears them (history remains in audit).
- reason >= 4 chars when true.
- audit before/after in same transaction; return `{question: QuestionDTO, audit_id: 123}`.

## 6. Tasks

### GET `/api/v1/admin/tasks`

Query `status`, `q` (code/question/username/error), page.

`TaskDTO` (matches current `AdminTask`):

```json
{
  "id": 2041,
  "code": "T-2041",
  "questionId": 1042,
  "userId": 1,
  "question": "求函数 ...",
  "username": "student01",
  "stage": "analysis",
  "targetIndex": null,
  "status": "failed",
  "errorCode": "AI_TIMEOUT",
  "errorMessage": "AI 服务响应超时，请重试",
  "retryIndex": 1,
  "createdAt": "11-27 22:41:08",
  "startedAt": "11-27 22:41:10",
  "finishedAt": "11-27 22:41:40",
  "duration": "30 秒"
}
```

`duration` is display-only: "30 秒", "生成中", "等待 75 秒", "已取消", etc.

### GET `/api/v1/admin/tasks/{id}`

Same DTO plus `timeline`:
`[{key,title,status,time,meta}]`; real dates, no duplicated slice hack.

### POST `/api/v1/admin/tasks/{id}/retry`

Only failed; max `retry_index < 3`; sets queued, clears errors, increments retry_index; audit.
Returns `{task: TaskDTO, audit_id: 123}`. If the worker is disabled, the task remains queued
and is still a valid real DB state.

### POST `/api/v1/admin/tasks/{id}/cancel`

Only queued; sets canceled/finished_at and clears errors; audit. Returns
`{task: TaskDTO, audit_id: 123}`.

## 7. AI logs

### GET `/api/v1/admin/ai-logs`

Query `status=success|error|invalid|all`, `operation`, `q` (user/model/prompt/error/id), page.

`AiLogDTO`:

```json
{
  "id": 9001,
  "time": "11-27 22:41:08",
  "username": "student01",
  "operation": "analyze",
  "model": "deepseek-flash",
  "promptVersion": "analyze_v3",
  "status": "error",
  "latency": "30.0s",
  "queueWait": "0.4s",
  "tokens": "—",
  "inputTokens": null,
  "outputTokens": null,
  "keySource": "system",
  "errorCode": "AI_TIMEOUT",
  "questionId": 1042,
  "hasRaw": true
}
```

Never include `raw` in list responses.

### GET `/api/v1/admin/ai-logs/{id}`

Same DTO; no raw.

### POST `/api/v1/admin/ai-logs/{id}/raw`

Body `{"reason":"排查超时"}`; reason >= 2 chars; writes `ai_log.view_raw` audit;
returns `{"raw":"...","truncated":false,"audit_id":123}`.
`raw` is capped at 8000 chars (same as service). `Cache-Control: no-store`.

## 8. Audit

### GET `/api/v1/admin/audit`

Query `q` (admin/action label/target/reason/request id/ip), `result`, page.

`AuditDTO`:

```json
{
  "id": 501,
  "time": "11-27 22:49:12",
  "admin": "admin",
  "action": "password_request.approve",
  "target": "student05",
  "targetType": "password_request",
  "targetId": "301",
  "reason": "用户名与注册邮箱一致，审批通过",
  "result": "success",
  "ip": "10.0.1.8",
  "requestId": "req_7f3a91",
  "before": null,
  "after": {"status": "approved"},
  "errorMessage": null
}
```

Search must match the Chinese action label as well as the raw action code. Keep the raw
action code for audit detail; list UI can translate it.

### GET `/api/v1/admin/audit/{id}`

Same DTO, full before/after.

### GET `/api/v1/admin/audit/export.csv`

Returns a UTF-8 BOM CSV with Chinese headers, quoted fields, current filters, max 1000 rows;
writes `audit.export` audit. Optional but recommended; frontend may call it.

## 9. Alerts

Alerts are **derived from real data**; acknowledgement state is stored in `admin_alert_acks`.

### GET `/api/v1/admin/alerts`

```json
[
  {
    "id": "tasks_failed",
    "severity": "critical",
    "title": "3 个任务连续失败",
    "detail": "最近 15 分钟有 3 个任务失败，最早 22:38。",
    "time": "11-27 22:41",
    "status": "active",
    "acknowledgedBy": null,
    "acknowledgedAt": null,
    "rule": "最近 15 分钟失败任务 ≥ 3",
    "current": 3,
    "threshold": 3,
    "target": {"type":"task","label":"任务中心","to":"/tasks?status=failed"}
  }
]
```

Derive at least: `tasks_failed`, `password_pending`, `ai_latency` (P95 > 45s in 1h),
`ai_error_rate` (>10% error+invalid in 1h). If a condition is no longer true, omit the alert.
If an ack row exists for an active condition, status is `acknowledged`; otherwise `active`.

### POST `/api/v1/admin/alerts/{key}/ack`

Body `{"note":"..."}` optional; inserts/updates ack; audit; returns the current alert DTO.
### POST `/api/v1/admin/alerts/{key}/unack`

Removes ack; audit; returns 204.

## 10. System

### GET `/api/v1/admin/system`

```json
{
  "generated_at": "11-28 01:20:00",
  "environment": {
    "app_env": "development",
    "is_demo": true,
    "version": "0.1.0",
    "llm_mode": "mock",
    "worker_enabled": true,
    "database": "sqlite"
  },
  "status": {
    "level": "ok",
    "summary": "运行正常",
    "active_alerts": 0
  },
  "checks": [
    {"key":"api","name":"API 网关","status":"ok","value":"正常","detail":"/health 200 · 42ms",
     "checkedAt":"11-28 01:20:00","meta":"探活"},
    {"key":"database","name":"数据库","status":"ok","value":"3 ms",
     "detail":"SELECT 1 通过","checkedAt":"11-28 01:20:00","meta":"探活"},
    {"key":"worker","name":"任务队列","status":"ok","value":"运行 0 · 并发 6",
     "detail":"排队 0 · 失败 0","checkedAt":"11-28 01:20:00","meta":"快照"},
    {"key":"llm","name":"大模型服务","status":"ok","value":"mock",
     "detail":"LLM_MOCK=true","checkedAt":"11-28 01:20:00","meta":"配置"}
  ],
  "config": [
    {"label":"应用版本","value":"0.1.0","note":"build 未注入"},
    {"label":"任务并发","value":"6","note":"TASK_MAX_CONCURRENCY"}
  ],
  "events": [
    {"time":"11-28 01:20:00","title":"数据库探活通过","detail":"SELECT 1","level":"ok"}
  ]
}
```

No fake `staging`/`real`; use the actual `settings.app_env` and `settings.llm_mock`.
`is_demo` is true when `app_env` is development/local or `llm_mock` is true.

## 11. Backend data changes

- `users`: `role` (student/admin, default student), `disabled_at`, `disabled_reason`,
  `must_change_password` (default false), `temp_password_expires_at`.
- `questions`: `hidden_at`, `hidden_reason`, `flagged_at`, `flag_reason`.
  `status` already exists; use `confirmed` / `hidden`.
- New `password_reset_requests` (fields in docs/agent/28 §6.2).
- New `admin_audit_logs` (fields in docs/agent/28 §6.3).
- New `admin_alert_acks` (`alert_key` PK, `acknowledged_by`, `acknowledged_at`, `note`).
- Add migration `admin_console` with SQLite batch mode and MySQL-safe DDL.
- Student question list/detail must exclude `status='hidden'`; admin endpoints include them.
- `UserResponse` adds `role` and `must_change_password`; existing tests must still pass.
- `get_current_user` rejects disabled accounts; `require_admin` checks role and disabled.
- CORS default includes `http://localhost:5174` for admin dev.
- Seed script: `scripts/seed_admin.py` using `ADMIN_USERNAME`, `ADMIN_PASSWORD`,
  `ADMIN_EMAIL`; no default password; production guard; idempotent. Add env example entries.
  It may create a pending password request for a demo student and a few AI logs only when
  `--demo` is passed; do not fake data by default.
- Tests: `tests/test_admin_api.py` covering 401/403, overview, users disable/force logout,
  question moderation, task retry/cancel, password approve/reject, audit, raw gate, alerts,
  system. Use the existing `db`/`client` fixtures. Do not weaken existing tests.

## 12. Frontend behavior

- Keep the current Calm Academic UI; replace `src/mock/data.ts` reads with a real data store.
- `src/api/client.ts`: fetch wrapper, base `/api/v1`, Bearer token from
  `bababoi:admin-token`, 401 -> clear and redirect `/admin/login`.
- `src/api/admin.ts`: typed functions for every endpoint above; map responses to
  `src/types.ts` shapes where possible.
- `src/stores/auth.ts`: real login via `/admin/auth/login`, role check, `/admin/me` on boot,
  independent token key; no mock credentials.
- `src/stores/adminData.ts`: state arrays for users/passwordRequests/questions/tasks/aiLogs/
  auditLogs/alerts, `overview`, `system`; `loadAll()`; mutation actions that call API and refresh.
  All counts/badges derive from this store.
- `AdminShell`: badges from store (`pendingPasswordCount`, `activeAlertCount`, `failedTaskCount`);
  remove hardcoded DEMO/mock text; show live environment only if available; keep UI.
- `LoginView`: real form; no hardcoded admin/admin123; show API errors; keep demo block only
  behind an explicit `VITE_ADMIN_DEMO` flag if needed.
- Views: keep templates and class names, replace mock imports and local mutations with store
  calls; add load-on-mount; show API errors as `Message.error`; do not invent fields.
- Mobile: fix fixed drawer widths to `min(width, 100vw)`; this is part of the real system.
- Run `pnpm typecheck` and `pnpm build` in `admin/` before reporting.

## 13. Non-goals for this pass

- Email/SMS delivery, student status page, multi-admin RBAC, teacher role.
- Real LLM calls or generated content changes.
- Prometheus/Redis/ELK, background alert scheduler.
- Enforcing `must_change_password` on student routes is backend-ready but student-frontend
  enforcement is a separate task; do not modify `frontend/` in this pass.
- No commits/pushes unless explicitly requested.
