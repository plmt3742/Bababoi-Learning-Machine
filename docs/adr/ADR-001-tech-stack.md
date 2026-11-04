# ADR-001: 技术栈确认

- 状态：Accepted
- 日期：2026-11-04
- 更新：2026-11-05（后端 Python 版本改为 3.13）
- 决策人：霹雳马桶、人机
- 相关任务：SH-001、FE-001、BE-001、OPS-001
- 相关文档：`docs/agent/05-architecture.md`、`docs/agent/10-resources.md`

## 1. 背景

实验室复试要求在 25 天内（11.7 / 11.14 / 11.21 / 11.29 四个截止）与搭档完成一个可演示的 AI 错题整理系统。`Resource/` 中的大创申报书写的是 SpringBoot + langchain4j，但该文档是早期申报材料，不是本次实现约束。团队已确认以下技术栈：

- 前端：Vue 3 + Vite + Arco Design Vue
- 后端：Python 3.13 + FastAPI
- 数据库：SQLite（本地/测试）+ MySQL 8（部署）
- AI：OpenAI 兼容接口，服务端调用
- 部署：Docker Compose + nginx，GitHub Actions CI

## 2. 决策

按上述技术栈执行；不引入 SpringBoot/langchain4j，不做模型训练，不引入 Redis/Celery/图数据库/向量库。

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Arco Design Vue + Vue Router + Pinia + Axios |
| 渲染 | markdown-it + KaTeX + DOMPurify |
| 图表 | ECharts |
| 后端 | Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic + Uvicorn |
| 认证 | JWT（PyJWT）+ bcrypt/argon2 |
| AI | DeepSeek `deepseek-flash`（OpenAI 兼容，文本+图像）；服务端调用；结构化 JSON |
| 数据库 | SQLite 本地/测试；MySQL 8 部署；schema 由人机负责 |
| 部署 | Docker Compose + nginx；GitHub Actions |

## 3. 后果

### 正面

- Python 在 LLM 接入、JSON 处理、异步/流式、快速迭代上更直接，适合 25 天交付。
- FastAPI 自带 OpenAPI，前后端契约更容易落地。
- SQLite 降低本地启动成本；MySQL 满足部署/演示。
- Vue3 + Arco 是团队已确认/熟悉的技术，减少学习成本。
- Docker Compose 可复现，适合实验室演示。

### 负面/代价

- 与 docx 的技术路线不一致，答辩需要能解释“为什么改”。
- SQLite/MySQL 双支持会增加兼容性成本（见 R-008）。
- Arco Design Vue 2.59 没有 Chat/Markdown/Charts 组件；Upload 无分块上传/相机 capture；聊天/流式面板、Markdown 渲染、图表都要自建或接第三方，需预留时间。
- Vue 3.5 与 Arco 有社区报告的兼容问题（Tooltip+Table、virtual-scroller+Collapse）；脚手架需 spike，必要时锁 Vue 3.4。
- Arco 主题若用 CSS 变量，必须覆盖完整 1–10 色阶，不能只改主色；若用 Less 覆盖，构建配置更复杂。
- Python 3.13 与部分库的版本兼容需要锁版本；用 uv 固定 3.13，并在 BE-001 后尽早做依赖兼容 spike。
- DeepSeek 只有 `deepseek-flash` 支持图片输入；`deepseek-v4-pro` 仅文本。识图依赖单一模型，供应商故障时只能退回文本。
- 图片识图按图片 token 计费，延迟高于纯文本；需要限制图片大小/次数，并准备文本兜底。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 双数据库差异 | 只写 ORM；Alembic 双跑；11.14 前 MySQL staging 验证 |
| Arco 组件缺失 | 先用现有组件；聊天/流式面板自建但保持简单 |
| DeepSeek 识图不可用/超时 | 文本入口保底；识图结果可编辑；演示缓存；备用 key |
| 技术栈被质疑 | 准备 1 页“选型理由”，强调交付效率/AI 生态/团队分工 |
| 依赖版本漂移 | 提交 lock 文件；关键依赖升级单独 PR |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| SpringBoot + langchain4j | 与 docx 一致；Java 生态成熟 | 与已确认栈冲突；团队后端更合适 Python；迭代慢 | 已确认 Python/FastAPI |
| Node/Express + Vue | 前后端同语言 | AI 生态/数据处理不如 Python；与已确认栈冲突 | 已确认 FastAPI |
| PostgreSQL | 更强的 JSON/全文/并发 | 与已确认“SQLite+MySQL”冲突；部署成本高 | 已确认 MySQL |
| 纯 SQLite 部署 | 最简单 | 并发/备份/多用户弱；不符合“MySQL 部署” | 保留为演示降级方案 |

## 5. 实施要点

- 前端用 TypeScript；API 类型尽量由 OpenAPI 生成或手写对照。
- 后端 Python 3.13 用 `uv` 固定；提交 `uv.lock`。
- 数据库 schema 由人机负责；霹雳马桶只提字段/查询需求，`05-architecture.md` 第 5 节是草案。
- SQLAlchemy 2.0 + Alembic；不写方言 SQL；不用数据库 JSON 查询。
- AI key 只在后端 `.env`；前端只有 `VITE_API_BASE_URL`。
- 部署从 11.7 开始 spike，11.14 必须有 staging。

## 6. 复审条件

- 11.14 仍无可用部署地址 → 重新评估部署方案/数据库。
- 双数据库兼容问题超过 1 天 → 考虑演示统一 SQLite，MySQL 仅作部署目标。
- Arco Vue 缺少关键组件且自建成本 > 2 天 → 评估替代组件库（需两人确认）。
- 性能/并发明显不够 → 再评估 async/PostgreSQL/缓存。

## 7. 链接

- `docs/agent/01-project.md` 第 9 节（与 docx 的差异）
- `docs/agent/05-architecture.md`
- `docs/agent/09-risks.md` R-008、R-009、R-012
- `docs/adr/ADR-003-image-input-vision.md`
