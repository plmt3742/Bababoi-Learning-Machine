# AGENTS.md — Bababoi Learning Machine

本文件是任何 AI agent 进入本仓库时的**第一入口**。先读这里，再按需加载 `docs/agent/` 下的文档。

## 项目一句话

把一道错题变成三道同类题，并追踪掌握度的 AI 错题巩固平台。

- 仓库：https://github.com/plmt3742/Bababoi-Learning-Machine
- 产品定位：学生录入错题 → AI 分析知识点/错误原因 → 生成 3 道相似题 → 练习 → 统计薄弱点
- 当前阶段：M0 产品设计 + 技术选型 + 仓库搭建（截止 11.7 24:00）
- 详细上下文：`docs/agent/00-context.md`

## 团队与分工

| 成员 | GitHub | 角色 | 负责 |
|---|---|---|---|
| 林敬翔（霹雳马桶） | @Plmt3742 | 前端 | Vue3 + Vite + Arco Design、前端部署、设计/测试共担 |
| 周彧良（人机） | @zhouyuliang0606 | 后端 | Python 3.12 + FastAPI、数据库、AI 接入、部署/测试共担 |
| 刘星宇 | — | 产品经理 | 定期会议、风险同步、体验走查、产品意见（不负责初期设计） |

## 已确认技术栈（以此为准）

- 前端：Vue 3 + Vite + Arco Design Vue（建议 TypeScript）
- 后端：Python 3.12 + FastAPI
- 数据库：SQLite（本地开发/测试）+ MySQL 8（部署）
- AI：DeepSeek `deepseek-flash`（OpenAI 兼容，文本 + 图像原生多模态），服务端调用，密钥不进前端
- 部署：Docker Compose + nginx（目标），GitHub Actions（CI）

> `Resource/基于生成式AI的错题整理系统.docx` 只是题目参考，不是准则。文档中的 SpringBoot/langchain4j、模型训练、知识图谱等内容与已确认技术栈冲突时，**以本文件和 `docs/agent/01-project.md` 为准**。

## 必读顺序

| 你要做什么 | 先读 |
|---|---|
| 第一次进入项目 | [00-context](docs/agent/00-context.md) → [01-project](docs/agent/01-project.md) → [03-roadmap](docs/agent/03-roadmap.md) → [04-todos](docs/agent/04-todos.md) |
| 写前端 | [00-context](docs/agent/00-context.md) → [05-architecture](docs/agent/05-architecture.md) → [06-file-tree](docs/agent/06-file-tree.md) → [07-workflow](docs/agent/07-workflow.md) |
| 写后端 | [00-context](docs/agent/00-context.md) → [05-architecture](docs/agent/05-architecture.md) → [06-file-tree](docs/agent/06-file-tree.md) → [07-workflow](docs/agent/07-workflow.md) |
| 做产品/原型设计 | [00-context](docs/agent/00-context.md) → [01-project](docs/agent/01-project.md) → [08-design-playbook](docs/agent/08-design-playbook.md) → [docs/product](docs/product/README.md) |
| 修 bug / 排查风险 | [00-context](docs/agent/00-context.md) → [09-risks](docs/agent/09-risks.md) → [05-architecture](docs/agent/05-architecture.md) |
| 准备答辩/PPT | [00-context](docs/agent/00-context.md) → [01-project](docs/agent/01-project.md) → [09-risks](docs/agent/09-risks.md) → [08-design-playbook](docs/agent/08-design-playbook.md) |
| 查资料/术语 | [10-resources](docs/agent/10-resources.md) |
| 切换会话/换 agent | [11-agent-handoff](docs/agent/11-agent-handoff.md) |

## 事实来源优先级

1. 代码与 OpenAPI 实际输出（实现细节）
2. `docs/agent/05-architecture.md` 中的 API 契约（协作约定）
3. `docs/agent/01-project.md`、`02-goals.md`（范围与目标）
4. 其他文档
5. `Resource/` 中的 docx（仅背景参考）

发现冲突时：不要默默按自己的理解做；先改文档或在 PR 中标注，再改代码。

## 硬性规则

- **不要修改 `Resource/`**：那是本地只读参考材料；**不要上传到仓库**（已在 `.gitignore`）。
- **不要提交密钥**：API Key、JWT Secret、数据库密码只放 `.env` / 服务器环境变量；仓库只提交 `.env.example`。
- **不要在浏览器端调用 LLM**：所有 AI 调用必须经过后端。
- **不要扩大范围**：先做 P0 演示闭环，P1/P2 见 `02-goals.md`。任何新功能先问“是否在 11.29 演示路径上”。
- **改结构/改契约必须同步文档**：至少更新 `05-architecture.md`、`06-file-tree.md`、`04-todos.md` 中受影响的部分。
- **不要提交无法运行的 main**：PR 必须过 lint/test/build；小步提交，短分支。
- **不要删除失败测试来“通过”**：修实现或明确标注已知失败。
- **不要凭记忆写库 API**：脚手架和关键依赖以官方文档为准，并在 PR 描述里贴出版本。

## 常用命令（脚手架完成后补充）

```bash
# 前端
cd frontend && pnpm install && pnpm dev

# 后端
cd backend && uv sync && uv run uvicorn app.main:app --reload

# 一键起本地依赖（MySQL 等）
docker compose -f deploy/docker-compose.dev.yml up -d

# 测试
cd frontend && pnpm test
cd backend && uv run pytest
```

> 当前仓库尚未初始化前后端代码，以上命令是目标状态；M0 完成脚手架后回来更新本节。

## 共享边界

- 本文件是**项目级共享规则**，不是林敬翔的个人偏好；对方 AI 可以读，也应该读。
- 个人学习笔记/个人 agent 配置放本地 `docs/learning/`（已 gitignore，不在仓库中）。
- 如果本文件与对方工具的全局规则冲突，**以项目代码/API 契约为准**，并在 PR/Issue 说明。
- 不要在本文件写密钥、token、私人信息、个人聊天记录。

## 文档维护

- 每个文档头部有 `owner`、`last_updated`、`read_when`。
- 里程碑结束时更新 `00-context.md`、`03-roadmap.md`、`04-todos.md`。
- 任何不可逆决策写进 `docs/adr/`。
- 文档索引：`docs/README.md`；agent 专用加载指南：`docs/agent/README.md`。
