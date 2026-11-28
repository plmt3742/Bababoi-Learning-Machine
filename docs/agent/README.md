# Agent 加载指南

> owner: 霹雳马桶 · last_updated: 2026-11-28 · read_when: 第一次让 agent 接手本仓库任务

这份文档告诉 agent **按什么顺序读、读多少、以什么为准、改完要同步什么**。目标是用最少的上下文完成任务，避免“读了全部文档仍然做错”。

## 1. 默认加载顺序

任何新会话，先读这三份，通常不超过 200 行：

1. [00-context.md](00-context.md) — 项目是什么、现在到哪一步、下一步做什么
2. [04-todos.md](04-todos.md) — 当前可领取的任务与验收标准
3. [05-architecture.md](05-architecture.md) 的“API 契约”和“数据模型”两节 — 不要凭记忆写接口

然后按任务类型追加：

| 任务类型 | 追加读取 | 不要读 |
|---|---|---|
| 前端页面/组件 | [06-file-tree.md](06-file-tree.md)、[07-workflow.md](07-workflow.md)、[03-page-specs.md](../product/03-page-specs.md) | 后端实现细节 |
| 后端接口/数据库 | [06-file-tree.md](06-file-tree.md)、[07-workflow.md](07-workflow.md)、[09-risks.md](09-risks.md) 的数据库/AI 部分 | 前端组件细节 |
| 产品/原型设计 | [01-project.md](01-project.md)、[08-design-playbook.md](08-design-playbook.md)、[product/README.md](../product/README.md) | 部署细节 |
| 修 bug | [09-risks.md](09-risks.md) 对应条目、[05-architecture.md](05-architecture.md)、相关代码 | 全部产品文档 |
| 部署/CI | [07-workflow.md](07-workflow.md)、[06-file-tree.md](06-file-tree.md) 的 `deploy/` 部分 | 产品设计 |
| 答辩/PPT | [01-project.md](01-project.md)、[02-goals.md](02-goals.md)、[09-risks.md](09-risks.md)、[08-design-playbook.md](08-design-playbook.md) 的答辩部分 | 代码细节 |
| 切换会话/换 agent | [11-agent-handoff.md](11-agent-handoff.md) | 全量重读 |

## 2. 事实来源优先级

1. **代码与 OpenAPI 实际输出**：实现细节的最终事实。
2. **`05-architecture.md`**：API / 数据模型 / 技术栈；改接口必须先改这里。
3. **范围 / 交互 / 验收**：`docs/product/01-prd-lite.md` + `02-ia-and-flows.md` + `03-page-specs.md`。
4. **`01-project.md` / `02-goals.md`**：摘要与目标；不单独新增范围。
5. **`03-roadmap.md` / `04-todos.md`**：进度与任务；判断“现在做什么”看这里。
6. **`Resource/` 的 docx**：背景参考，不是准则。

冲突处理：**范围/交互/验收 → PRD；API/数据/技术 → 05**；跨域变更两边同时升版本。不要自行选一个执行，先在 PR/Issue 里标注冲突，更新对应文档，再改代码。

> `12`–`21` 是按日期编号的**历史对接记录**（不是现行契约）；现行口径以 `05-architecture.md` 与 `docs/adr/` 为准。
> 其中 `16`、`17` 已归档（`status: archived`），只用于追溯当时的取舍，引用时用「16 号 §x / 17 号 §x」。

## 3. 任务 ID 约定

| 前缀 | 范围 |
|---|---|
| `DS-` | 设计（Design） |
| `FE-` | 前端 |
| `BE-` | 后端 |
| `OPS-` | 部署、CI、环境 |
| `SH-` | 两人共同/项目管理 |
| `R-` | 风险（Risk） |
| `Q-` | 开放问题（Question） |

引用任务时写完整 ID，例如“完成 FE-012 后开始 BE-010”。不要只写“那个列表页”。

## 4. 状态图例

`TODO` 未开始 · `DOING` 进行中 · `DONE` 已完成 · `BLOCKED` 被阻塞 · `DEFERRED` 明确延期/不做 · `PROPOSED` 待确认 · `ACCEPTED` 已确认。

## 5. 写代码前的自检

- [ ] 这个任务在 `04-todos.md` 里有 ID 和验收标准吗？
- [ ] 接口在 `05-architecture.md` 里有定义吗？没有就先加，或和对方确认。
- [ ] 文件放在 `06-file-tree.md` 规定的位置了吗？
- [ ] 是否碰到 `09-risks.md` 里的高风险项？碰到就先读缓解措施。
- [ ] 是否在 `Resource/` 里写东西？**不允许**。
- [ ] 是否把密钥写进代码/文档？**不允许**。

## 6. 改完要同步什么

| 你改了什么 | 必须同步 |
|---|---|
| API 路径/字段/错误码 | `05-architecture.md`、OpenAPI、前端 `api/types.ts` |
| 数据表/字段/迁移 | `05-architecture.md` 数据模型、`06-file-tree.md`（如新增目录） |
| 新增页面/组件目录 | `06-file-tree.md`、`docs/product/03-page-specs.md` |
| 任务完成/阻塞 | `04-todos.md`、GitHub Issue |
| 范围变化 | `01-project.md`、`02-goals.md`、ADR |
| 不可逆技术决策 | `docs/adr/` 新增 ADR |
| 新的高风险 | `09-risks.md` |

## 7. 上下文预算建议

- 单次任务优先读 **3 份以内**文档；不要一次性把 `docs/` 全读。
- 需要历史决策时读 `docs/adr/`，不要翻聊天记录。
- 需要原始题目背景时读 [10-resources.md](10-resources.md) 的摘要；只有摘要不够才打开 docx。
- 长文档（`05-architecture.md`、`08-design-playbook.md`、`09-risks.md`）按标题跳读，不要整篇加载。
- 文档超过 600 行时，优先拆分成“速览 + 细节”两份，而不是继续追加。

## 8. 当前快照（每次里程碑更新）

- 阶段：11.29 演示收尾（11.22–11.29）
- 头号目标：学生端闭环连续 3 次成功；管理端按 ADR-009 展示已实现能力；PPT/备用录屏就绪
- 已确认：大学理科优先（通用后续）、Python 3.13、DeepSeek `deepseek-flash` 多模态、图片 v2（裁剪 + 多题文本提取）、数据库 schema 由人机负责、两位开发共同负责产品设计
- 设计产出：01/02/04/06/07/08 已定稿；03 页面规范部分完成（新增 4.6.1 忘记密码）；07/08/原型待按图片 v2 更新
- 当前代码：`origin/main` 已合学生端闭环、管理端文档与后端地基（#123）；FE-001~039 已合
- 前端：FE-001~039 已合；FE-040 待 BE-030
- 管理端：ADR-005 + ADR-009；`admin/` 进入 11.29 演示（范围见 `28-admin-console.md`）；后端地基 #123 已合，前端 PR #120 待合，主分支 `admin/` 仍为占位
- 头号风险：范围过大 + 演示网络/额度（见 `09-risks.md` R-001、R-010）
- 下一步：BE-015/BE-016；ADM-003/004/007/008/011 端点/页面；BE-030/ADM-010/FE-040 密码申请；部署/彩排
- 新会话交接：用 [11-agent-handoff.md](11-agent-handoff.md) 的提示词
