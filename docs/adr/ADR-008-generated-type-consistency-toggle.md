# ADR-008: 生成题题型一致性改为用户设置开关

- 状态：Accepted
- 日期：2026-11-07
- 决策人：霹雳马桶
- 相关任务：BE-026、FE-027
- 相关文档：`docs/agent/05-architecture.md` §6.9、`docs/agent/04-todos.md`

## 1. 背景

“生成相似题的题型必须与原题一致”此前在硬约束与软约束之间反复：当前分支的 `b5dea9e` 实现硬校验，#39 的三段并发实现软约束，两者共用 `generate_v2`，语义相反。产品需要一个可配置的稳定口径，而不是每次二选一。

## 2. 决策

新增用户级设置 `enforce_same_question_type`：

- **默认开启**；
- 按用户在后端持久化；
- 开启时：生成题题型必须与原题一致；不一致重试 1 次，仍不一致按 `AI_INVALID_OUTPUT` 失败；
- 关闭时：允许生成题换题型，照常入库；
- 前端在「个人设置 → 生成设置」提供开关；接口为 `GET/PUT /settings/preferences`；
- 后端生成链路读取该偏好，`ai_call_logs` 建议记录 `type_policy=strict|soft`，避免同版本号语义混淆。

## 3. 后果

- 默认行为符合此前 Q-018 的产品要求；
- 用户可按题型表达难度自行放宽；
- 需要新增用户偏好字段/接口、迁移与生成校验分支；
- 现有 #38 的无条件硬校验不再保留；硬校验由后端按开关执行。

## 4. 备选

| 方案 | 不选原因 |
|---|---|
| 全局硬约束 | 模型在部分题型上难以表达时会持续失败，用户无法自救 |
| 全局软约束 | 与产品“同类题”语义冲突，题型漂移无法控制 |
| 前端 localStorage 开关 | 换设备失效，后端生成链路无法感知，等于假开关 |

## 5. 链接

- Issue #44：`BE-026 用户生成偏好 + 题型一致性开关`
- Issue #43：`BE-025 完整三题型编辑 PATCH 扩展`
- 前端 PR：FE-027

## 6. 2026-11-10 补充（strict 落地前置）

> 本节追加，不改上面的决策。

- 默认 strict 仍是产品决策；但 strict 的实现必须同时包含两件事：
  1. 生成 prompt 明写「题型必须与原题一致」；`generate_v2` 现在是「首选…允许调整」的软措辞，不足以支撑判死。
  2. `prompt_version` 升到 `generate_v3`。prompt 文本变了，版本必须变，否则日志里分不清这条 strict 失败是哪版 prompt 出的。
- PR #58 不得以「软 prompt + strict 默认」合并。当前 main 仍是 `generate_v2` 软约束，strict 未启用。
- 真实数据口径：PR #58 里「生成题经常换题型」不成立。7 个红色队列测试用的是故意混合题型的 mock（`blank/solve/choice`）；真实 DeepSeek 冒烟 3/3 solve；ADR-006 记录 27/27 题型一致。**mock 的失败率不能当产品失败率**。
- 兜底：11.29 前 `generate_v3` 没落地，就演示默认关闭 strict（开关仍在，行为回到 soft）。
- 之前「只记 `type_policy`、不升 `prompt_version`」的说法对 strict 作废；soft 仍不升。
- 同步位置：`docs/agent/05-architecture.md` §6.9/§7.3、`docs/agent/18-backend-unfinished-api-sync-20261107.md` §1/§12、`docs/agent/20-three-segment-contract-sync-20261110.md` §4。
