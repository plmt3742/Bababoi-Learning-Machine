---
owner: 霹雳马桶 / 人机
last_updated: 2026-11-11
status: archived
read_when: 只在追溯 2026-11-06 三段并发的判据取舍时读；现行口径以 05 §6.4/§7.2/§7.3 与 ADR-006 为准
---

# 三段并发 · 落地结论（2026-11-06，已归档）

> 本文件整理自 2026-11-06 的三段并发对接记录，**保留原小节编号（§一–§八）**，供 05 / ADR-006 按号引用。
> 现行契约以 `05-architecture.md`（§6.4 / §7.2 / §7.3）与 ADR-006 为准；标注「已被取代」的条目只作历史依据。

## 一、与既定口径一致的部分

| 项 | 结论 |
|---|---|
| 一次生成排 3 段，每段 1 题（ADR-006） | 一致 |
| 返回 `{tasks:[{task_id,target_index,difficulty}]}` | 一致 |
| 整组收 `difficulties`，单段收 `target_index + difficulty` | 一致 |
| 入队即软删旧组（方案 a） | 一致 |
| 每段只写自己那格 | 一致 |
| 单段失败不牵连其余；requeue 前判 90s | 一致 |
| 并发 2 → 6 | 一致 |
| 两条新列迁移，upgrade/downgrade 实测 | 一致 |

真模型端到端段延迟 3.5–11.3s，与早期 A/B 实测（5.6–21.9s）同一量级。

## 二、相似度判据：改为「归一化后逐字相同」

- 0.9 相似度阈值没有鉴别力：实测判死 4/9、3/9，被判死的是 `x^2-a\ln x`、`ax-2\sqrt x`、`x+a/x` 这类换了函数族的正常新题；18 段里逐字抄题 0 段；合法输出最高 0.967 与「真抄」分布重叠。
- **结论**：判据从「相似度阈值」改为「**归一化后**逐字相同」。
- 归一化范围（已实现）：去所有空白、全角/半角统一、`$...$` 与 `\(...\)` 等价、`\left(`/`\right)` 等价；实现时又补了 `\displaystyle` 剥离、`\dfrac`/`\tfrac` 折成 `\frac`、半角 `,`/`;` 抹掉。
- **未覆盖**：`\ln` vs `\log_e` 这类语义等价，记为 P1 BE-022，不假装覆盖。
- 这条规则的唯一价值是拦真抄，漏判等于白写。

## 三、同组两格出同一函数式：P1 处理

- 现象：第 1 格 `2x-a\ln x` 讨论单调性、第 3 格同一函数式多挂一个小问。
- **结论**：P0 不做结构判据，记 P1 **BE-022「同组公式结构去重」**。理由：比较 `$...$` 表达式需要解析/规范化（`2x-a\ln x` 与 `2x - a \ln x` 算不算同一个），成本不小；误判会让用户看到「三题里有一题不能用」；P0 已有 `too_easy`/`too_hard` 用户反馈通道兜底。
- P0 原计划只在 `warnings` 里给「与第 n 题函数式相近」的提示、不判死；当时 `generated_questions` 没有 `warnings` 列，随 BE-014 一起做。

## 四、PR #38：backend 部分让位（历史）

- **事实**：#38（已关闭）的 backend 7 个文件与三段分支 100% 重叠，实现的是题型硬约束，版本号也叫 `generate_v2`——同版本号、相反语义，必冲突。
- **结论**：#38 只保留 `frontend/` 改动；`backend/README.md` 那 3 行由三段分支吸收。
- **定权**：`generate_v2` 只表示「一段一题 + 软约束题型」；题型硬约束要改就升 **`generate_v3`**。
- **后续**：BE-026 已落地 `generate_v3` = strict（用户开关开启时 prompt 写死同题型），soft 仍 `generate_v2`，见 05 §7.3。

## 五、双字段：不保留顶层 `task_id`（已核实）

- **结论**：`POST /questions/{id}/generate` 只返回 `tasks`，后端从未双发顶层 `task_id`；「兼容旧 `task_id`」指的是前端 FE-023 自己留的兜底分支，已删除（2026-11-10）。
- 后端无需改动。自核方式：`grep -rn "task_id" frontend/src | grep -v "tasks\["` 之后只应剩 `tasks[].task_id`。

## 六、推送前核对项与结果（当时）

1. **`target_index` 历史回填**：按 `parent_question_id, created_at, id` 给活跃行编 1/2/3；软删行与第 4 条以后留 NULL。已实现（迁移 `3f9c1a7e5b24`，逐行 UPDATE 以避开 MySQL 8 的子查询限制）。
2. **validator 无题型 `raise`**：已核，只有 `validate_type_payload` 的结构规则。
3. **`max_tokens`/`temperature`/`trust_env=False` 落在 `DeepSeekClient`**：已核。
4. **PR 只有 2 笔、base=main**：已核。
5. **downgrade 后老数据仍可读**：已补测（6 行老形状数据 upgrade → downgrade，行数与题面仍在）。注意 downgrade 后必须同时回滚代码，ORM 带着 `target_index` 会在老 schema 上报 `no such column`。

## 七、前端配套（前端负责）

- 三张卡不假设同题型，每张卡自带题型徽章；混排时按实际类型渲染。
- 整组软删的中间态显示「正在替换，已就绪 n/3」。
- 失败卡单独提供【重新生成】，其余两张正常展示。
- `target_index` 缺失时按 `created_at` 兜底排序（防回填遗漏）。

## 八、结论

三件拍板：判据收紧为归一化后逐字相同、同函数式去重放 P1、#38 缩到 `frontend/`；顶层 `task_id` 不保留。

## 附录：后端处置记录（2026-11-06）

| 条目 | 处置与结论 | 落点 |
|---|---|---|
| §二 归一化后逐字相同 | 采纳，并补强：旧归一化只去空白与常见标点，`\left(`、`\,` 这类换排版会漏；补 `\left`/`\right`/`\displaystyle` 剥离、`\dfrac`/`\tfrac` 归一、半角标点抹除。`\ln` vs `\log_e` 不做，记 P1 | `ai/validator.py::_normalize_for_compare`、05 §7.2 |
| §三 同函数式先不判死、记 P1 | 采纳，记为 BE-022；P0 提示待 `warnings` 列（随 BE-014） | 04-todos BE-022、ADR-006 §4 |
| §四 #38 缩到 frontend、`generate_v2` 定权 | 采纳；`backend/` 7 文件让位 | 05 §7.3 |
| §五 删顶层 `task_id` | 前提与实现不符：后端从未双发，顶层 `task_id` 只在 `/analyze` 返回；要删的是前端兜底 | 05 §6.4 |
| §六-1 迁移回填 | 采纳并实现（原实现确实缺回填） | 迁移 `3f9c1a7e5b24` |
| §六-2/3/4 | 已核：validator 无题型 raise；采样参数与 `trust_env` 已落；PR 2 笔、base=main | 代码 / git |
| §六-5 downgrade 后老数据可读 | 已补测；附「downgrade 必须同时回滚代码」提醒 | 迁移验证脚本（本地） |
| §七 前端配套 | 后端不依赖；回填完成后前端兜底只剩迁移前老库场景 | — |
