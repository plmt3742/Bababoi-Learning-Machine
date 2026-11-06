---
owner: 霹雳马桶
last_updated: 2026-11-06
status: active
read_when: 后端对接、三段并发/图片/草稿/统计联调、PR 合并状态
---

# 15 · 后端对接同步（2026-11-06）

> 对象：人机
> 基线：`main @ 7ee6029`（#6/#5/#9 已合）
> 前端已完成：#19/#21/#23~#25/#28~#30/#34/#35（FE-013/014/016/018/020/021/023/024 + 首页）
> 本文可直接发给后端；详细三段并发口径见 [14-generation-three-segments-reply.md](14-generation-three-segments-reply.md)
> 2026-11-07 更新：生成题题型一致性改为用户设置开关（ADR-008），默认开启；`from-image` 的 `subject`/`chapter`/`difficulty` 三项可空。以本文、05 v0.6.6 与 ADR-008 为准。

## 1. 先确认：上一轮阻塞已清零

你已经修掉并合入 main 的两条，前端复核通过：

1. **analysis 写回正字段**：`AnalysisResult` / prompt 补 `answer_md` / `explanation_md`；`_apply_analysis` 只在原题字段为空时写回，原题已有不覆盖。
2. **标签不再被冲掉**：`sync_tags(..., merge=True)`，AI 知识点追加，用户手动标签保留。
3. 额外：`TaskOut.error_message` 已补，任务中心可以显示具体失败原因。

#6/#5/#9 CI 绿、已合；main CI 绿。

## 2. 口径更新：生成题题型一致性改为用户设置开关

> 2026-11-07 产品确认，覆盖本文件旧「软约束」与另一分支的「硬约束」二选一表述；见 ADR-008。

- 新增用户级设置 `enforce_same_question_type`，**默认开启**，按用户后端持久化；
- 开启时：生成题题型必须与原题完全一致（choice → choice，blank → blank，solve → solve）；不一致带原因重试 1 次，仍不一致按 `AI_INVALID_OUTPUT` 失败，不入库；
- 关闭时：允许换题型，照常入库（#39 的软约束行为）；
- **不新增 `TYPE_MISMATCH`**，段失败沿用 `AI_*` / `INTERNAL_ERROR`；
- 接口：`GET/PUT /settings/preferences`；生成链路读取用户偏好；
- 05 v0.6.6 §7.2、ADR-008、ADR-006 已同步；`generate_v2` 的 prompt 保持软措辞，硬模式建议在 `ai_call_logs` 记录 `type_policy=strict|soft`。
- 图片提取同时新增 AI 初判：每道题返回 `subject`、`chapter`、`question_type`、`difficulty`（三项可空），前端预填、用户可改；prompt 版本按 BE-014 当前实现为准。

## 3. 后端下一步优先级

### P0：三段并发生成（新 PR，base=main）

请另开一个 base=main 的 PR，不要叠在 #5/#6/#9 上；随 PR 提交 **ADR-006**（ADR-005 已给 admin）。

必须包含：

| 项 | 口径 |
|---|---|
| 接口 | `POST /questions/{id}/generate` 返回 `{tasks:[{task_id,target_index,difficulty}]}`；请求整组收 `difficulties`，单段收 `difficulty` |
| 数据 | `generated_questions.target_index`；`generation_task.difficulty` |
| 替换 | 整组重生成按格替换（旧组软删 + 每段写自己的 slot）；不要一段成功删整组 |
| 重试 | 单段失败可单独 retry；一段失败不影响其余两段 |
| 并发 | `TASK_MAX_CONCURRENCY` 默认 6（可配）；单段 120s 硬超时；requeue 前判断 `now - started_at > 90s` |
| 取消 | P0 不做真取消；不新增 `/tasks/{id}/cancel`；前端只保留“暂停自动刷新” |
| 任务中心 | 一次生题 3 个任务；列表折叠“生题 2/3”+ 展开三段 |
| 校验 | 每段 1 题；题型一致性由 `enforce_same_question_type` 控制（默认开启=硬校验；关闭=软约束）；与原题、同组其它格只拒“归一化后逐字相同” |
| 错误码 | 不新增 `TYPE_MISMATCH`；段失败沿用 AI_* / INTERNAL_ERROR |

前端 FE-023 已按这个形状合入（#28），兼容旧的单 `task_id` 返回，所以你什么时候合都不会把现有详情页打挂。字段名如需调整，请在开三段 PR 前说。

### P0：BE-014 图片文本提取

前端 FE-016/021 已合（#29），mock 先行；请按 14 号文档 §5 和 05 v0.4 实现：

- `POST /uploads/images`：JPEG/PNG/WebP；服务端校验/压缩/去 EXIF；返回 `{image_path,url,width,height}`。
- `POST /questions/from-image`：返回 `{image_path, questions:[{index,content_md,question_type,options,blanks,has_figure,warnings,incomplete?}], warnings}`；不返回 bbox/candidates。
- **先转正再提取**：前端裁剪步骤提供左转/右转；后端也做方向判定。
- **压缩**：上传/落库 ≤2000px/5MB；送 LLM 前压到长边 1200。
- **超时**：P0 用 120s 同步、不自动重试；超时 `AI_TIMEOUT`，用户可重传/改文本；异步为 P1。
- **残缺条目**：提取并返回 `warnings` + `incomplete=true`，由用户确认时决定留不留。
- 探针脚本可提交 `backend/scripts/`；真实题图不进仓库，用合成/脱敏图。

### P1：BE-018 草稿接口

前端 FE-018 要做服务端 + localStorage 双写，需要：

- `GET /drafts/me` → `{content, version, updated_at}` 或 204
- `PUT /drafts/me` → 防抖覆盖；返回新 version
- `DELETE /drafts/me`
- 版本冲突返回 `409 DRAFT_VERSION_CONFLICT`；前端会做“保留本地/保留服务端”选择

### P1：BE-013 统计接口

FE-014 已按 mock 做完，后端请按同一形状实现 `GET /stats/overview`：

```text
total_questions, total_generated_questions, total_practice_records,
accuracy, mastered_count, reviewing_count, unmastered_count,
weak_knowledge_points: [{name, wrong_count, total_count, accuracy}],
recent_trend: [{date, practice_count, correct_count}],
updated_at
```

薄弱点按练习记录聚合到父题标签，Top 5；无练习记录时返回空数组，不要造数。

## 4. 其他后端待办

- BE-008 种子脚本：直接插 3 条 `generated_questions`（带 `target_index`/`difficulty`），不跑真模型。
- BE-009 OpenAPI：导出 `contracts/openapi/openapi.json`；前端后续生成类型。
- BE-011 MySQL：迁移在 MySQL 通过；utf8mb4；JSON/datetime/索引检查。
- OPS-001/002/005：compose + staging；11.14 前必须有可访问地址。
- **#8 docs**：你那条 PR 的 docs 状态已被 #26 覆盖；请关闭或 rebase 成只改 `backend/README.md` 的单独 PR，避免和 main 的 04/06 冲突。
- 合并后删除已合分支（#6/#5/#9、#7、#14 等），减少后续 rebase 噪音。

## 5. 前端状态（供你排期）

| 任务 | 状态 |
|---|---|
| FE-013 练习页 | ✅ #23 已合（mock 先行，等真接口联调） |
| FE-014 统计 | ✅ #24 已合（mock 先行，等 BE-013） |
| FE-020 三题型编辑器 | ✅ #25 已合 |
| FE-016/021 图片录入 + 多题条目 | ✅ #29 已合（mock `/uploads/images` + `/questions/from-image`；等 BE-014） |
| FE-023 三段并发 UI | ✅ #28 已合（兼容旧 `task_id`；等 ADR-006 真接口） |
| FE-018 草稿/可访问性 | ✅ #30 已合（服务端草稿 BE-018 尚缺，当前 mock） |
| FE-025 首页学习概览 | ✅ #34 已合 |
| FE-024 个人设置 / BYOK | ✅ #35 已合（等 BE-020 真接口；见 ADR-007/Issue #32） |

## 6. 需要你确认的两件事

1. **三段并发响应**：`{tasks:[{task_id,target_index,difficulty}]}` 是否最终定稿？前端 FE-023 已合（#28）并兼容旧 `task_id`；如果字段名要改，请在开三段 PR 前说。
2. **from-image 的 `incomplete`**：是否接受在 `questions[]` 里加 `incomplete: boolean` + `warnings: string[]`？前端会把残缺条目标出来让用户决定。
