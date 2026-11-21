---
owner: 霹雳马桶
last_updated: 2026-11-21
status: active
read_when: 后端实现改密/重置密码接口前；前端接“忘记密码”页前；联调密码相关接口时
---

# 26 · 密码接口对接单（改密 + 重置）

> 结论先说：
> 1. **修改密码**口径已定，前端 FE-038 已按 mock 接通，后端按 `BE-029` 实现即可（§2）。
> 2. **重置密码**当前没有邮件/验证码能力（`users.email` 只是可选字段，从未验证），需要先拍板验证方式；推荐邮箱验证码（§3），实现前不要写 OpenAPI。

## 1. 现状

- 后端 `/auth` 只有 `register` / `login` / `me`；无改密、无重置。
- `users.email` 可选、不验证；没有 SMTP、验证码表或发信服务。
- 前端设置页已有「账号安全」卡（FE-038），调用 `POST /auth/change-password`；后端 404/405 时自动降级为“后端未启用”。
- `Q-002` 目前写的是“不做找回密码/邮箱验证”；若走 §3 的方案，需要同步改成“邮箱验证码重置（P1）”。

## 2. 修改密码（已定，前端已接）

### 2.1 接口

```http
POST /api/v1/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{ "current_password": "旧密码", "new_password": "新密码" }
```

| 结果 | 响应 |
|---|---|
| 204 | 无 body |
| 400 `VALIDATION_ERROR` | 新密码少于 8 位 / 超过 72 字节 / 与旧密码相同 |
| 401 `AUTH_INVALID_CREDENTIALS` | 当前密码不正确 |
| 401 `AUTH_TOKEN_EXPIRED` | 登录失效（走全局 401） |
| 429 `AUTH_RATE_LIMITED` | 改密过于频繁 |

### 2.2 后端实现要点

- 用 `verify_password(current_password, user.password_hash)` 校验旧密码；失败返回 401 `AUTH_INVALID_CREDENTIALS`，**不要**返回“用户名不存在”之类的区分信息。
- 新密码长度按 **UTF-8 字节** 校验：`8 <= len(raw) <= 128` 且 `len(raw.encode("utf-8")) <= 72`（bcrypt 只取前 72 字节，见 `core/security.py`）。
- 新旧相同直接 400，避免“改了个寂寞”。
- 更新 `password_hash` 后**吊销旧 token**：建议随 `BE-028 token_version` 一起做（`token_version += 1`，`get_current_user` 校验版本）；否则旧 JWT 还能用满 7 天。
- 限流：按用户 5 次/分钟；不要求按 IP（已登录）。
- 日志只记 user_id / 状态码，不记 body、密码、hash。

### 2.3 前端现状（FE-038）

- 设置页「账号安全」：当前密码 + 新密码 + 确认；8–72 字节、新旧不得相同、两次一致。
- 当前密码错误只在页内提示，不会清 token（`client.ts` 已把该端点的 401 从全局登出里排除）。
- 成功后清会话、回登录页并提示“密码已更新，请用新密码重新登录”。
- 联调时只需确认：204、错误码、以及“成功后旧 token 是否失效”。

## 3. 重置密码（待拍板，推荐邮箱验证码）

### 3.1 先拍板

| 方案 | 可行性 | 代价 | 结论 |
|---|---|---|---|
| **A. 邮箱验证码** | `users.email` 已有；需要 SMTP 或邮件 API | 2 个接口 + 1 张表 + 发信配置 | **推荐** |
| B. 管理员重置 | 无需发信；但 admin 未建（ADR-005 明确 P1 不做重置密码） | 需要 admin 用户管理 + 临时口令下发 | 不推荐（本期） |
| C. 安全问题 | 需要新增问题/答案字段与 UI，答案可被社工 | 中 | 不推荐 |
| D. 只凭用户名重置 | 任何人可接管任意账号 | 无 | **禁止** |

若选 A，需要确认：**能不能提供 SMTP**（或 SendGrid/阿里云邮件等 HTTP 发信）。没有发信能力就退到“联系管理员人工处理”，不做自动重置。

### 3.2 接口（方案 A）

```http
POST /api/v1/auth/password-reset/request
{ "username": "student01" }
```

- 无论用户是否存在、是否有邮箱，一律返回：

```http
202 { "message": "如果账号存在并绑定了邮箱，验证码已发送" }
```

- 存在且有邮箱：生成 6 位数字码，`sha256(code)` 入库，10 分钟有效；发送邮件。
- 限流：同一用户 60 秒 1 次、10 次/天；同一 IP 5 次/小时。超限返回 429 `AUTH_RATE_LIMITED`。
- 不返回邮箱掩码，避免枚举；前端只展示泛化提示。

```http
POST /api/v1/auth/password-reset/confirm
{ "username": "student01", "code": "123456", "new_password": "新密码" }
```

| 结果 | 响应 |
|---|---|
| 204 | 无 body |
| 400 `RESET_CODE_INVALID` | 验证码错误（剩余次数 > 0） |
| 400 `RESET_CODE_EXPIRED` | 验证码过期或不存在 |
| 400 `VALIDATION_ERROR` | 新密码不合规（同 §2.2） |
| 429 `AUTH_RATE_LIMITED` | 尝试过于频繁 |

- 校验通过：更新 `password_hash`、删除该用户的验证码、`token_version += 1`、204。
- 连续错 5 次：删除验证码并让本次重置失效；用户需重新 request。
- 成功后可选发一封“密码已修改”通知邮件（本期可不做）。

### 3.3 数据表（迁移）

```text
password_reset_codes
- id            bigint pk
- user_id       bigint not null unique  -> users.id
- code_hash     varchar(64) not null    -- sha256(code)
- expires_at    datetime not null
- attempts      int not null default 0
- created_at    datetime not null
```

一个用户只保留一条有效记录；request 时 upsert，confirm 成功/失败超限时删除。不要存明文验证码。

### 3.4 配置

```dotenv
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_STARTTLS=true
PASSWORD_RESET_TTL_MINUTES=10
# 仅本地开发：把验证码打到服务端日志，生产必须为 false/不设置
PASSWORD_RESET_CODE_LOG=false
```

- 生产缺 SMTP：`request` 仍返回 202（不暴露配置状态），但服务端记 warning；不要把“未配置”返回给客户端。
- 本地无 SMTP：开 `PASSWORD_RESET_CODE_LOG=true`，从 uvicorn 日志取码联调；**不要**在 API 响应里返回验证码。
- 发信失败：仍返回 202；服务端记 error + user_id，验证码保留，用户可重新 request（受 60 秒限流）。

### 3.5 前端规划（FE-039，依赖 BE-030）

- 登录页「忘记密码」入口 → 用户名 → 验证码 + 新密码 + 确认。
- `request` 的 202 只显示泛化提示；没有邮箱/没收到时提示“请联系管理员”。
- 429 显示倒计时；`RESET_CODE_INVALID` / `RESET_CODE_EXPIRED` 原地提示，不跳页。
- 成功后回登录页，复用 FE-038 的“密码已更新，请用新密码重新登录”提示。

## 4. 需要确认 / 拍板的点

1. 重置方式是否走 **A. 邮箱验证码**？
2. 有没有 **SMTP / 邮件 API** 可用？如果没有，重置是否直接降级为“联系管理员”？
3. `email` 是否要顺便做“绑定/验证”？本期可以不做，但重置只对填了邮箱的账号有效。
4. `BE-028 token_version` 是否随 BE-029/BE-030 一起合？不合并的话，“改密/重置后旧 token 立即失效”无法保证。

## 5. 联调验收

- 改密：旧密码错 401 且前端不被踢；正确 204；旧 token 401；新密码可登录。
- 改密限流：连续 6 次 429。
- 重置 request：存在/不存在/无邮箱都 202，响应不可区分；60 秒内重复 429。
- 重置 confirm：正确 204；错误码 400；过期 400；错 5 次失效；新密码可登录；旧 token 401。
- 日志：无密码、无验证码、无 token 明文。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-21 | 新建：改密口径（FE-038/BE-029）与重置方案 A（BE-030/FE-039） |
