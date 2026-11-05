---
owner: 霹雳马桶
last_updated: 2026-11-05
status: active
read_when: 查资料、术语、docx 原文摘要、外部文档链接时
---

# 10 · 资料与术语

## 1. 本地资料

| 路径 | 内容 | 使用方式 |
|---|---|---|
| `Resource/基于生成式AI的错题整理系统.docx` | 大创项目申报书（背景、研究内容、技术路线、预期成果） | **只读**；需要背景/动机时查摘要；不要修改 |
| `docs/agent/01-project.md` | 本项目最终范围与决策 | 与 docx 冲突时以此为准 |
| `docs/product/` | 产品设计产出（PRD、IA/流程、页面规范、设计 tokens、线框/交互地图） | 设计阶段的主文档 |
| `docs/adr/` | 技术/范围决策 | 需要历史原因时读 |

> `Resource/` 是**本地只读参考材料，不提交到仓库**。不要在里面对文件做“整理/重命名/转格式”；需要引用就复制摘要到本文档。新环境 clone 后没有 `Resource/` 是正常的。

## 2. docx 摘要

### 2.1 它是什么

一份“大学生创新创业训练计划”项目申报书，主题是“基于生成式 AI 的错题整理系统”。它描述的是**长期愿景**，不是本次 25 天实验室考核的交付清单。

### 2.2 核心内容

| 章节 | 要点 |
|---|---|
| 项目简介 | 录入错题 → AI 分析 → 生成 3 道相似题；持久化存储、图像识别、智能生成 |
| 研究目的 | 提升错题收集效率、无纸化、输出相似题加强巩固 |
| 研究内容 | 错题分析与知识点挖掘、相似题生成与质量评估、用户体验优化 |
| 技术路线 | 前端 Arco Design；后端 SpringBoot + langchain4j；MySQL；流式消息 |
| 预期成果 | 生成 3 道相似题、错题分类/标签/搜索、学习进度/正确率/个性化反馈 |
| 进度 | 2025.5–2026.12 四阶段（与实验室 11.7–11.29 不同） |
| 已有基础 | 前端熟悉 Vue3/Arco；后端熟悉 Java/Docker/langchain4j；缺高质量错题数据集 |
| 创新点 | AI 深度融合、动态学习优化（机器学习/强化学习） |

### 2.3 对本次开发有用的部分

- 产品动机：错题整理耗时、纸质本不便、只会一道题。
- 核心闭环：录入 → 分析 → 生成 3 题 → 练习 → 统计。
- 预期成果：分类/标签/搜索、学习进度、正确率、个性化反馈。
- 前端技术：Arco Design、流式消息输出。
- 质量意识：生成题需要质量评估（可做人工抽检 + 结构校验）。

### 2.4 不要照搬的部分

| docx | 问题 | 本项目做法 |
|---|---|---|
| SpringBoot + langchain4j | 与已确认技术栈冲突 | Python 3.13 + FastAPI + OpenAI 兼容 SDK |
| 模型训练/强化学习 | 25 天不可行；无数据集 | 不训练；Prompt + 结构化输出 + 校验 |
| 知识图谱 | 成本高，演示收益低 | 标签 + 学科 + 统计 |
| 图像识别作为核心 | 独立 OCR 对公式/图表/手写体不稳定 | 不做独立 OCR；DeepSeek `deepseek-flash` 多模态识图；P0 增强；结果可编辑；文本兜底 |
| 个性化推荐算法 | 无数据/无时间 | 规则 + 统计（薄弱知识点排序） |
| 2025–2026 四阶段 | 与实验室截止冲突 | 以 11.7/11.14/11.21/11.29 为准 |
| “动态学习/模型进化” | 无法在演示中证明 | 作为未来规划，不硬吹 |

## 3. 事实来源与冲突处理

优先级从高到低：

1. 代码 + OpenAPI 实际输出
2. `05-architecture.md` 的 API 契约
3. `01-project.md` / `02-goals.md`
4. `03-roadmap.md` / `04-todos.md`
5. 其他文档
6. `Resource/` docx（背景参考）

冲突时：**先改文档，再改代码**；在 PR/Issue 标注冲突，不要默默选一个。

## 4. 外部资料

> 脚手架/关键依赖以官方文档为准；下面链接用于查最新版本和配置，不要在文档里硬编码可能过期的 API。

### 前端

| 主题 | 链接 | 用途 |
|---|---|---|
| Vue 3 | https://vuejs.org/guide/ | Composition API、`<script setup>` |
| Vite | https://vite.dev/guide/ | 配置、代理、环境变量 |
| Arco Design Vue | https://arco.design/vue/docs/start | 组件、主题、按需引入 |
| Vue Router | https://router.vuejs.org/ | 路由、守卫 |
| Pinia | https://pinia.vuejs.org/ | 状态管理 |
| Axios | https://axios-http.com/ | 拦截器、错误处理 |
| markdown-it | https://markdown-it.docschina.org/ | Markdown 渲染 |
| KaTeX | https://katex.org/docs/ | 数学公式 |
| DOMPurify | https://github.com/cure53/DOMPurify | XSS 清洗 |
| ECharts | https://echarts.apache.org/ | 统计图表 |
| dayjs | https://day.js.org/ | 时间格式化 |

### Arco 集成调研（2026-11）

| 主题 | 链接 | 结论 |
|---|---|---|
| 快速开始 | https://arco.design/vue/en-US/docs/start | Vue ≥ 3.2；支持按需引入 |
| 主题 | https://arco.design/vue/en-US/docs/theme | Less `modifyVars` 构建时覆盖 |
| 暗色 | https://arco.design/vue/en-US/docs/dark | `body[arco-theme='dark']` |
| Design Token | https://arco.design/vue/en-US/docs/token | CSS 变量/RGB 通道 |
| Upload | https://arco.design/vue/en-US/component/upload | 有 `custom-request`；无分块/相机 capture |
| ConfigProvider | https://arco.design/vue/en-US/component/config-provider | `global` 影响命令式 API |
| Comment | https://arco.design/vue/en-US/component/comment | 页面评论，不是聊天 |
| List | https://arco.design/vue/en-US/component/list | 有虚拟列表，可做消息列表基础 |
| 组件清单 | https://github.com/arco-design/arco-design-vue/tree/main/packages/web-vue/components | 无 Chat/Markdown/Charts |
| 版本 | https://github.com/arco-design/arco-design-vue/releases | 当前 2.59.x（2026-10-20） |
| Pro Vue 模板 | https://github.com/arco-design/arco-design-pro-vue | 用 ECharts + `@arco-plugins/vite-vue` |
| Tailwind 冲突 | https://github.com/arco-design/arco-design-vue/issues/759 | preflight 覆盖 Button；注意 CSS 顺序 |
| Vue 3.5 兼容 | https://github.com/arco-design/arco-design-vue/issues/3390 | Tooltip + Table 问题；先 spike |
| 虚拟列表兼容 | https://github.com/arco-design/arco-design-vue/issues/3642 | Vue 3.5 + virtual-scroller/Collapse |
| Vite 插件 | https://github.com/arco-design/arco-plugins/tree/main/packages/plugin-vite-vue | 样式/主题/图标；1.4.6 |

> 以上是调研结论，不替代实际安装验证。脚手架时以 `package.json` 锁定的版本和官方文档为准。

### 后端

| 主题 | 链接 | 用途 |
|---|---|---|
| FastAPI | https://fastapi.tiangolo.com/ | 路由、依赖、SSE、OpenAPI |
| Pydantic v2 | https://docs.pydantic.dev/ | 请求/响应/AI 输出校验 |
| SQLAlchemy 2.0 | https://docs.sqlalchemy.org/en/20/ | ORM、双数据库 |
| Alembic | https://alembic.sqlalchemy.org/ | 数据库迁移 |
| Uvicorn | https://www.uvicorn.org/ | ASGI server |
| PyJWT | https://pyjwt.readthedocs.io/ | JWT |
| pwdlib | https://github.com/frankie567/pwdlib | 密码哈希（或 bcrypt） |
| OpenAI Python SDK | https://github.com/openai/openai-python | OpenAI 兼容接口 |
| httpx | https://www.python-httpx.org/ | HTTP 客户端/测试 |
| pytest | https://docs.pytest.org/ | 测试 |
| Ruff | https://docs.astral.sh/ruff/ | lint/format |
| uv | https://docs.astral.sh/uv/ | Python 依赖/版本 |
| Pillow | https://pillow.readthedocs.io/ | 图片处理 |

### 部署/工具

| 主题 | 链接 | 用途 |
|---|---|---|
| Docker Compose | https://docs.docker.com/compose/ | 本地/部署编排 |
| nginx | https://nginx.org/en/docs/ | 静态资源/反向代理/SSE |
| GitHub Actions | https://docs.github.com/actions | CI |
| GitHub Flow | https://docs.github.com/get-started/using-github/github-flow | 分支/PR |
| Conventional Commits | https://www.conventionalcommits.org/ | commit 规范 |
| Mermaid | https://mermaid.js.org/ | 文档图示 |
| Figma | https://www.figma.com/ | 高保真/原型 |
| Excalidraw | https://excalidraw.com/ | 线框/流程 |
| 即时设计 | https://js.design/ | Figma 替代（国内访问） |
| Playwright | https://playwright.dev/ | E2E |
| Vitest | https://vitest.dev/ | 前端单测 |

### 供应商/模型（11.5 spike 用）

| 主题 | 链接 | 备注 |
|---|---|---|
| OpenAI API | https://platform.openai.com/docs/ | 兼容接口参考；国内访问需评估 |
| DeepSeek 平台 | https://platform.deepseek.com/ | **已定为默认供应商** |
| DeepSeek 图像理解 | https://api-docs.deepseek.com/zh-cn/guides/vision | `deepseek-flash` 支持图片；JPEG/PNG/GIF/WebP；图片只放 user 消息 |
| DeepSeek Files API | https://api-docs.deepseek.com/zh-cn/guides/files_api | 复用图片/大图；MVP 可不用，直接 base64 |
| DeepSeek 更新日志 | https://api-docs.deepseek.com/zh-cn/updates | 确认模型版本/能力 |
| 阿里云百炼/Qwen | https://help.aliyun.com/zh/model-studio/ | 备用文本/视觉供应商（非默认） |
| 智谱 GLM | https://open.bigmodel.cn/ | 备用文本/视觉供应商（非默认） |

> **已定**：默认 DeepSeek `deepseek-flash`（文本 + 识图）；`deepseek-v4-pro` 不支持图片。11.5 spike 只验证 JSON、识图质量、延迟、价格、限流；备用供应商只在 DeepSeek 不可用时考虑。

## 5. 术语表

| 术语 | 含义 | 本项目中的用法 |
|---|---|---|
| 错题 | 学生做错的题目 | `questions` 表；含题干/答案/分析/标签 |
| 相似题 | 与原题同知识点、同题型、同难度，但情境/数字不同的题 | `generated_questions`；一次 3 道 |
| 知识点 | 题目考查的概念/方法 | `tags.type=knowledge_point`；3–5 个 |
| 题型 | 题目形式/考点类型 | 如“导数与极值”“线性方程组” |
| 难度 | easy/medium/hard | 由 AI 判断 + 人工抽检 |
| 掌握度 | 通过练习正确率/薄弱点近似衡量 | 统计页；不是严格心理测量 |
| 多模态识图 | 多模态 LLM 直接读图片，返回题干/公式/图形描述 | DeepSeek `deepseek-flash`；结果可编辑；**不做独立 OCR** |
| OCR | 传统图片转文本管线 | 本项目不使用独立 OCR 服务 |
| SSE | Server-Sent Events | 阶段级生成进度；`text/event-stream` |
| JWT | JSON Web Token | 登录态；`Authorization: Bearer` |
| 软删除 | 标记 `deleted_at` 而非物理删除 | 保护统计/误删 |
| 幂等 | 同一请求重复执行结果一致 | 防重复提交/重复生成 |
| 熔断 | 连续失败后暂时停止调用 | AI 供应商故障时 |
| 降级 | 主路径失败时走备用路径 | SSE 失败回退同步；AI 失败回退缓存 |
| 纵向切片 | 端到端跑通一条最小功能链 | M1：登录→录入→生成→保存 |
| 契约先行 | 先定 API/数据模型再写代码 | 前后端并行 |
| Walking Skeleton | 最小可运行骨架 | M0/M1 |
| ADR | Architecture Decision Record | `docs/adr/` |
| DoD | Definition of Done | `07-workflow.md` |
| P0/P1/P2 | 优先级 | P0 演示必须；P1 有余力；P2 未来 |
| RAG | Retrieval-Augmented Generation | 本项目 MVP 不用；不要硬加 |
| 知识图谱 | 实体/关系图谱 | P2；MVP 用标签 |

## 6. 需要收集的参考数据

| 数据 | 数量 | 用途 | 负责人 |
|---|---|---|---|
| 大学理科错题（高数/线代/概率/大学物理） | 20 道 | Prompt 调试、人工抽检、种子数据 | 两人 |
| 每题答案/解析 | 20 份 | 质量评估 | 两人 |
| 长题干/公式题 | 5 道 | 渲染压力测试 | 霹雳马桶 |
| 图片题（清晰，含公式/图表） | 5 张 | DeepSeek 识图测试 | 人机 |
| 演示用清晰题图 | 3 张 | 现场识图演示 | 霹雳马桶 |
| 演示账号 | 2 个 | 演示 | 两人 |
| 练习记录 | 20+ 条 | 统计页 | 人机 |
| 用户测试反馈 | 3–5 人 | 可用性/答辩 | 霹雳马桶 |
| 生成质量抽检 | 20 组 | 答辩数据 | 人机 |

## 7. 文档/资料维护规则

- 外部链接失效时，更新链接或删掉；不要留死链。
- 版本号/API 以官方文档为准；本文档只做索引，不复制大段文档。
- 新术语先加到术语表，再在文档里使用。
- docx 摘要只保留“对开发有用”的内容；不要全文复制。
- 本地原始资料放 `Resource/`（不上传仓库）；仓库只放摘要到 `docs/agent/10-resources.md`，不要散落在根目录。
