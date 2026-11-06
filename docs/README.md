# 项目文档总索引

本目录分三层：

| 目录 | 用途 | 谁维护 |
|---|---|---|
| `docs/agent/` | 给 AI agent 和人快速加载的工程上下文：项目信息、目标、进度、待办、架构、文件树、工作流、风险、资料 | 两人共同维护 |
| `docs/product/` | 产品设计产出：PRD、信息架构与流程、页面规范、设计系统 | 两位开发共同负责，产品评审参与 |
| `docs/adr/` | 架构决策记录（Architecture Decision Record） | 提出决策的人 |

## 从哪里开始

- **第一次进入项目**：[agent/00-context.md](agent/00-context.md)
- **看当前要做什么**：[agent/03-roadmap.md](agent/03-roadmap.md) + [agent/04-todos.md](agent/04-todos.md)
- **写代码前**：[agent/05-architecture.md](agent/05-architecture.md) + [agent/06-file-tree.md](agent/06-file-tree.md)
- **做设计前**：[agent/08-design-playbook.md](agent/08-design-playbook.md) + [product/README.md](product/README.md)
- **查风险/答辩**：[agent/09-risks.md](agent/09-risks.md)
- **查资料/术语**：[agent/10-resources.md](agent/10-resources.md)
- **切换会话/换 agent**：[agent/11-agent-handoff.md](agent/11-agent-handoff.md)

## 文档清单

### Agent 上下文

| 文件 | 内容 | 何时读 |
|---|---|---|
| [agent/README.md](agent/README.md) | agent 加载策略、维护规则、状态图例 | 第一次让 agent 接手任务 |
| [agent/00-context.md](agent/00-context.md) | 一页纸速览：项目、团队、栈、当前阶段、下一步 | 每次新会话 |
| [agent/01-project.md](agent/01-project.md) | 项目定义：背景、用户、范围、非目标、约束、开放问题 | 需要判断“该不该做” |
| [agent/02-goals.md](agent/02-goals.md) | 产品/技术/交付目标、验收标准、指标 | 需要判断“做到什么程度算完成” |
| [agent/03-roadmap.md](agent/03-roadmap.md) | 时间线、里程碑、当前进度、周计划 | 每次开工/收工 |
| [agent/04-todos.md](agent/04-todos.md) | 按角色和优先级拆分的任务，含 ID/验收标准 | 领取任务/同步进度 |
| [agent/05-architecture.md](agent/05-architecture.md) | 系统架构、技术选型、数据模型、API 契约、AI 流水线 | 写前后端代码前 |
| [agent/06-file-tree.md](agent/06-file-tree.md) | 目标文件树、目录职责、命名规范、文件放置决策树 | 新建文件/目录前 |
| [agent/07-workflow.md](agent/07-workflow.md) | Git/PR/评审/联调/部署/测试/会议/DoD | 第一次提交前 + 每周复盘 |
| [agent/08-design-playbook.md](agent/08-design-playbook.md) | 原型设计、工作流设计、交付物、检查清单、答辩准备 | 设计阶段 |
| [agent/09-risks.md](agent/09-risks.md) | 风险登记册 + 实现注意事项 + 演示兜底 | 每周复盘 + 答辩准备 |
| [agent/10-resources.md](agent/10-resources.md) | 本地资料、docx 摘要、外部链接、术语表 | 查资料 |
| [agent/11-agent-handoff.md](agent/11-agent-handoff.md) | 新会话交接提示词、角色模板、交接检查 | 切换会话/换 agent |
| [agent/12-backend-alignment.md](agent/12-backend-alignment.md) | 后端对接结果：队列、图片 v2、PRD、分支合并决策 | 后端对接 / M0 契约确认 |
| [agent/13-backend-merge-audit.md](agent/13-backend-merge-audit.md) | 后端合并审查、未合并分支 review、CI 方案 | 合并审查 / 交接 |
| [agent/14-generation-three-segments-reply.md](agent/14-generation-three-segments-reply.md) | 三段并发生成：Q1–Q7、PRD/05 改动、图片实测回复 | 三段并发 / 生成链路 |
| [agent/15-backend-sync-20261106.md](agent/15-backend-sync-20261106.md) | 后端对接同步：已合 PR、下一步、接口确认 | 后端对接 / 联调 |

### 产品设计

| 文件 | 内容 | 状态 |
|---|---|---|
| [product/README.md](product/README.md) | 设计产出索引与当前状态 | 有效 |
| [product/PRD.md](product/PRD.md) | 完整产品契约：范围/交互/验收（从 `docs/prd` 分支合并，修订 v0.9） | 待合并 |
| [product/PRD-v0.8-reference.md](product/PRD-v0.8-reference.md) | PRD v0.8 归档参考；不构成契约 | 归档 |
| [product/开源项目调研.md](product/开源项目调研.md) | 11 个开源项目参考；答辩/PPT 素材 | 归档 |
| [product/01-prd-lite.md](product/01-prd-lite.md) | 一页纸 PRD 速览（大学理科、闭环、P0/P1/P2、指标） | 已定稿 |
| [product/02-ia-and-flows.md](product/02-ia-and-flows.md) | 信息架构、sitemap、3 条核心流程、AI 状态机 | 已定稿 |
| [product/03-page-specs.md](product/03-page-specs.md) | 页面规范模板（8 个核心页面；示例+要点已填） | 部分完成 |
| [product/04-design-system.md](product/04-design-system.md) | 设计 tokens + 组件清单 + 状态矩阵 | 已定稿 |
| [product/05-ue-spec.md](product/05-ue-spec.md) | UE 稿/交互地图规范与模板 | 模板 |
| [product/06-draft-dual-write.md](product/06-draft-dual-write.md) | 草稿：服务端 + localStorage 双写、接口、冲突处理 | 已定稿 |
| [product/07-page-drafts.md](product/07-page-drafts.md) | 8 个关键页面的线框级设计 | 已定稿（待按图片 v2 更新） |
| [product/08-interaction-map.md](product/08-interaction-map.md) | 页面交互地图、跳转关系、数据流、状态机 | 已定稿（待按图片 v2 更新） |
| [product/drafts/prototype.html](product/drafts/prototype.html) | 可本地打开的页面原型（8 页线框） | 旧框题版；待更新 |
| [product/drafts/interaction-map.html](product/drafts/interaction-map.html) | 可本地打开的页面地图（HTML，点击页面框打开原型） | 旧框题版；待更新 |

### 架构决策

| 文件 | 内容 | 状态 |
|---|---|---|
| [adr/README.md](adr/README.md) | ADR 索引与写法 | 有效 |
| [adr/ADR-000-template.md](adr/ADR-000-template.md) | ADR 模板 | 模板 |
| [adr/ADR-001-tech-stack.md](adr/ADR-001-tech-stack.md) | 技术栈确认（含与 docx 的差异） | Accepted |
| [adr/ADR-002-mvp-scope.md](adr/ADR-002-mvp-scope.md) | MVP 范围与 P0/P1/P2 | Proposed |
| [adr/ADR-003-image-input-vision.md](adr/ADR-003-image-input-vision.md) | 图片输入：DeepSeek 多模态直读，不做独立 OCR | Accepted |
| [adr/ADR-004-image-text-extraction.md](adr/ADR-004-image-text-extraction.md) | 图片录入：用户裁剪 + 文本提取 + 多题条目 | Accepted |
| [adr/ADR-005-admin-console.md](adr/ADR-005-admin-console.md) | 独立 admin 管理端（P1 内部运维台） | Accepted |
| [adr/ADR-007-user-ai-key.md](adr/ADR-007-user-ai-key.md) | 用户自带 AI API Key（BYOK）设置 | Accepted |

## 状态图例

| 标记 | 含义 |
|---|---|
| `TODO` | 未开始 |
| `DOING` | 进行中 |
| `DONE` | 已完成 |
| `BLOCKED` | 被阻塞，需在每日同步中提出 |
| `DEFERRED` | 明确延期/不做，附原因 |
| `PROPOSED` | 待团队确认 |
| `ACCEPTED` | 已确认 |

## 文档维护规则

1. **小文件优先**：单个文档尽量控制在 300 行以内；架构/风险等核心长文档可到 600+ 行，但必须按节加载，不要整篇塞进上下文。
2. **单一事实来源**：任务状态以 `04-todos.md` + GitHub Issues 为准；API 以 OpenAPI 为准；范围以 `01-project.md` 为准。
3. **先改文档再改代码**：涉及 API、数据模型、目录结构的改动，PR 中必须同时更新文档。
4. **里程碑结束必须更新**：`00-context.md`、`03-roadmap.md`、`04-todos.md` 的状态与“下一步”。
5. **决策留痕**：不可逆或影响两人的决策写 ADR，不要只留在聊天记录里。
6. **不要复制大段 docx**：`10-resources.md` 只放摘要和链接，原文留在 `Resource/`。

## 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-11-04 | 初始化文档体系 | 霹雳马桶 / agent |
| 2026-11-04 | 确认大学理科、DeepSeek 多模态识图、数据库 schema 归人机；新增 ADR-003、11-agent-handoff、.gitignore | 霹雳马桶 / agent |
| 2026-11-05 | 同步产品设计状态：01/02/04/06/07/08 已定稿，03 部分完成，原型可用；补充 12-backend-alignment | 霹雳马桶 / agent |
| 2026-11-05 | 同步 origin/main：补 13-backend-merge-audit；新增 ADR-004 图片文本提取 v2；后端通知 issue #13 | 霹雳马桶 / agent |
| 2026-11-06 | 同步前端进度：FE-009/019（PR #19）与全量 Calm Academic 视觉覆写（PR #21）已合入 main；旧 PR #20 关闭；更新 00/03/04/11 + 04 design system + 02/06/07 + frontend README | 霹雳马桶 / agent |
| 2026-11-06 | 新增 ADR-005：独立 `admin/` 为 P1 内部运维台，不进入 11.29 演示；同步 01-project/06-file-tree/README/AGENTS | 霹雳马桶 / 人机 |
| 2026-11-06 | 会话交接同步：main @ 7ee6029；前端 FE-001~024 页面完成；后端剩余 BE-014/BE-018/BE-013/BE-020/ADR-006；新增 ADR-007 BYOK | 霹雳马桶 / agent |
