# ADR-007: 用户自带 AI API Key（BYOK）设置

- 状态：Accepted
- 日期：2026-11-06
- 决策人：霹雳马桶、人机
- 相关任务：FE-024（前端）、BE-020（后端）
- 相关文档：`docs/agent/05-architecture.md`、`docs/agent/04-todos.md`、Issue #32

## 1. 背景

当前 AI 调用统一使用系统 `.env` 里的 DeepSeek Key。用户提出希望在「个人设置」里导入自己的 OpenAI 兼容 API Key，生成/分析时优先使用自己的 Key。

这是安全敏感功能：

- Key 是用户资产，泄露会造成直接经济损失；
- 前端不能直接调用 LLM（05 §9.4）；Key 不能进 localStorage/Pinia/日志；
- 自定义 `base_url` 可能被用于 SSRF；
- 用户自己的 Key 可能额度/模型不同，失败模式要可解释。

## 2. 决策

**在「个人设置」中提供 BYOK 配置；Key 只提交到后端，后端加密存储，生成/分析时优先使用用户 Key，未配置回退系统 Key。**

### 2.1 接口

```text
GET /api/v1/settings/ai
→ { configured, provider, base_url, model, api_key_masked, updated_at }

PUT /api/v1/settings/ai
body { provider, base_url?, model, api_key }
→ 同上（只返回 masked）

DELETE /api/v1/settings/ai
→ 204
```

- `api_key_masked` 形如 `sk-****abcd`；任何响应/日志/错误体不得包含原始 Key。
- `provider`: `deepseek` | `openai_compatible`。
- `provider=deepseek` 时 `base_url` 可为空，使用默认；`openai_compatible` 必须 `https`。
- 建议只允许白名单 host（至少 `api.deepseek.com` / `api.openai.com`）；放开自定义 host 必须先做 SSRF 防护（禁止内网/回环/metadata）。

### 2.2 存储

- 新表 `user_ai_settings`：
  - `user_id` PK/FK
  - `provider`
  - `base_url`
  - `model`
  - `api_key_ciphertext`
  - `key_last4`
  - `created_at` / `updated_at`
- 加密密钥从环境变量 `SETTINGS_ENCRYPTION_KEY` 读取（Fernet/AES-GCM），不进仓库。
- 数据库只存密文 + nonce/tag；不存明文。
- 删除配置 = 删除行；不保留旧 Key。

### 2.3 使用顺序

1. 用户配置的 Key（如果 configured）
2. 系统 `.env` 的 Key
3. `LLM_MOCK=true` 时 mock，不调用真实模型

`ai_call_logs` 记录 `key_source=user|system`，**不记录 Key 本身**。

### 2.4 前端

- `/settings` 页：账号信息 + AI API 设置。
- 密码型输入 + 显示/隐藏；保存后清空输入，只显示 masked。
- 不写 localStorage/Pinia；不打印 Key。
- 明确提示「密钥只提交到服务端，前端不保存、不回显完整值；生成时由后端使用」。

## 3. 后果

### 正面

- 用户可以用自己的额度/模型，降低系统 Key 成本与额度压力。
- 配置项可控，未来可扩展到多 provider/多模型。
- 安全边界清晰：Key 只在服务端。

### 负面/代价

- 新增加密密钥管理、迁移与后台任务取 Key 逻辑。
- 自定义 base_url 带来 SSRF 风险，需要白名单/校验。
- 用户 Key 失效/额度不足时，错误要能区分并提示；不能静默回退（否则用户不知道自己的 Key 没用上）。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| Key 泄露到前端/日志 | 只返回 masked；前端不落库；日志过滤；测试扫描 |
| SSRF | https + host 白名单；禁止内网/回环/metadata |
| 用户 Key 失效 | 明确 `AI_PROVIDER_ERROR` / `AI_INVALID_KEY` 错误码，提示检查设置 |
| 加密密钥丢失 | `SETTINGS_ENCRYPTION_KEY` 备份到密码管理器；丢失则用户重新填 Key |
| 用户 Key 被用于他人任务 | 取 Key 必须按 `user_id`；worker 任务带 user_id；越权测试 |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| 前端直接调用 LLM | 实现快 | Key 必泄露，违反 05 §9.4 | 安全不可接受 |
| Key 存 localStorage | 简单 | XSS 直接偷 Key | 安全不可接受 |
| 只用系统 Key | 零改动 | 不满足用户自带 Key 需求；成本集中 | 需求明确要求 |
| 每个请求临时传 Key | 不存储 | Key 每次经过网络/日志，体验差 | 不采用 |

## 5. 验收

- 未配置时系统 Key 正常工作；配置后使用用户 Key。
- 响应/日志/DB 无明文 Key；前端无 localStorage/Pinia 副本。
- 越权、非法 base_url、Key 失效都有明确错误。
- 375/1366 页面可用；键盘/焦点/标签可访问。

## 6. 链接

- Issue #32
- `docs/agent/05-architecture.md` §6.9
- `docs/agent/04-todos.md` §1.7
- `frontend/src/views/SettingsView.vue`
- `backend/app/api/v1/settings.py`（待实现）
