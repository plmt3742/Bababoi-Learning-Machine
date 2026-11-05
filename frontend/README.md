# frontend

Vue 3 + Vite + TypeScript + Arco Design Vue。

> 状态：FE-001 ~ FE-012、FE-015、FE-019 已完成；FE-009/019 在 PR #19，全量 Calm Academic
> 视觉覆写在 PR #21（stacked，2026-11-06，均 CI 绿待合并）。应用壳、路由、设计 tokens、API
> client、Mock API、登录/注册与路由守卫已就位；错题录入、列表、详情、Markdown/公式渲染、
> 空/错/loading 状态、AI 生成进度轮询与任务中心已可用。练习、统计等仍待实现。

## 技术栈（实际安装版本）

| 依赖               | 版本                           |
| ------------------ | ------------------------------ |
| Vue                | 3.5.44                         |
| Vite               | 8.3.5                          |
| TypeScript         | 5.9.3（strict）                |
| Arco Design Vue    | 2.59.0                         |
| Vue Router         | 4.6.4                          |
| Pinia              | 3.0.4                          |
| Axios              | 1.21.0                         |
| axios-mock-adapter | 2.1.0（devDependency）         |
| markdown-it        | 15.0.3                         |
| KaTeX              | 0.19.1                         |
| DOMPurify          | 3.4.17                         |
| ESLint             | 10.14.0（flat config）         |
| Prettier           | 3.9.10                         |
| 组件自动导入       | unplugin-vue-components 32.1.0 |

## 环境要求

- Node.js ≥ 22.12（实测 v22.22.3）
- pnpm ≥ 9（实测 v11.7.0；`pnpm-lock.yaml` 为 lockfileVersion 9.0）
- 后端默认运行在 `http://127.0.0.1:8000`

## 常用命令

```bash
pnpm install       # 安装依赖
pnpm dev           # 开发服务器 http://127.0.0.1:5173
pnpm build         # vue-tsc 类型检查 + 生产构建（输出 dist/）
pnpm preview       # 预览生产构建
pnpm lint          # ESLint（0 warning）
pnpm lint:fix      # ESLint 自动修复
pnpm typecheck     # vue-tsc --noEmit
pnpm format        # Prettier 写入
pnpm format:check  # Prettier 检查
```

## 环境变量与代理

复制 `.env.example` 为 `.env.local` 后按需修改：

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_USE_MOCK=true
```

- 开发时 Vite 将 `/api` 代理到 `http://127.0.0.1:8000`（见 `vite.config.ts`）。
- 后端接口前缀是 `/api/v1`，例如 `GET /api/v1/health`。
- `VITE_USE_MOCK` 仅在开发环境生效：默认开启内存 Mock；设为 `false` 时走真实后端。
- Mock 通过 `axios-mock-adapter` 挂在共享 Axios 实例上，入口为
  `src/api/mocks/index.ts`，由 `main.ts` 动态导入，不会进入生产包。
- 前端只放 API 基地址；任何密钥、LLM Key 都不能进入前端环境变量。

## 登录与 Mock

- 演示账号：`student01` / `password123`。
- `/login` 支持登录/注册（注册成功自动登录）；登录后跳转到合法的 `redirect`
  或首页，`redirect` 只允许站内绝对路径。
- token 存放在 `localStorage` 的 `bababoi:token`；刷新时通过 `GET /auth/me`
  恢复用户，token 失效会清空登录态并回到 `/login`。
- 受保护页面通过 `meta.requiresAuth` + 全局路由守卫拦截；任意接口返回 401 会
  触发统一的清 token / 跳登录处理。
- Mock 覆盖：认证、错题 CRUD/筛选、创建后的分析任务、相似题生成任务、任务列表与重试、
  草稿 GET/PUT/DELETE、练习记录创建/列表。Mock 数据在内存中，刷新后新增数据会重置
  （演示账号保留）；种子题 101 自带 3 道生成题。
- Mock 任务时间线：`queued → running` 约 900ms，`running → done` 约 2400ms，接口统一
  320ms 延迟。`quiz` 任务完成后会为父题替换/创建 3 道 `generated_questions`，因此
  102/104 生成后轮询即可看到题卡；`analysis` 任务完成后补全通用分析。种子数据中的
  进行中任务也会按同一时间线推进，便于任务中心演示。

## 路由

使用 `createWebHistory`，每个路由通过 `meta.title` 同步浏览器标题。

| 路径             | 页面                         | 布局     |
| ---------------- | ---------------------------- | -------- |
| `/login`         | 登录/注册                    | 独立页   |
| `/`              | 首页占位                     | AppShell |
| `/questions`     | 错题列表（筛选/搜索/分页）   | AppShell |
| `/questions/new` | 录入错题（文本）             | AppShell |
| `/tasks`         | 任务中心（列表/筛选/重试）   | AppShell |
| `/questions/:id` | 错题详情（分析/生成题/删除） | AppShell |
| `/practice/:id?` | 练习占位（`id` 可选）        | AppShell |
| `/stats`         | 统计占位（P1）               | AppShell |
| 其余路径         | 404                          | AppShell |

## 错题页面（FE-007 / FE-008）

- **录入 `/questions/new`**：桌面两栏（左侧题干/答案/解析，右侧学科/章节/标签），
  移动端单栏；学科必选、题干必填且 ≤5000 字；保存调用 `POST /questions`，
  成功后跳转详情并提示分析任务已入队。当前按解答题保存，选项/空位编辑器留待 FE-020。
- **列表 `/questions`**：卡片列表，关键词搜索 300ms 防抖，学科/标签/掌握状态筛选与
  URL query 同步；分页默认 20 条。区分空账号与筛选无结果，错误可重试。
- **详情 `/questions/:id`**：按“原题 → AI 分析 → 生成进度 → 生成题 → 下一步”纵向排列；
  答案/解析默认折叠，分析未完成时显示等待/失败提示；生成相似题调用
  `POST /questions/{id}/generate` 后自动开始轮询，完成后自动刷新题卡；删除使用
  Arco Modal 二次确认。

## AI 任务轮询与任务中心（FE-009 / FE-019）

- `src/composables/useTaskPolling.ts` 封装 `GET /tasks` 轮询：同一时间只允许一个请求，
  组件卸载 / `reset` 后忽略迟到响应。
- 详情页用 `question_id` 过滤，每 **1.5s** 轮询；任务中心跨题展示，每 **2s** 轮询。
- 只要有 `queued` / `running` 任务就继续轮询；全部进入 `done` / `failed` 后自动停止。
- 手动「停止等待」只暂停本页刷新，服务器任务继续；超过 **120s** 仍未结束会显示慢任务提示。
- 详情页在分析/生题任务完成后自动 `GET /questions/{id}?include=generated`，无需手动刷新；
  失败的 `analysis` / `quiz` 任务可原地重试并恢复轮询。
- 任务中心包含状态筛选（全部/排队中/生成中/完成/失败）、任务行（任务号、阶段、状态、
  题目链接、创建时间、错误信息、失败重试）与草稿行（`GET /drafts/me`，有草稿时链接到
  `/questions/new`）。
- P0 不接 SSE；进度只走 `/tasks` 轮询。

## Markdown 与公式（FE-010）

- `src/components/common/MarkdownRenderer.vue` 封装
  `markdown-it + KaTeX + DOMPurify`，`html: false`，渲染结果统一过 DOMPurify。
- 支持行内 `$...$` 与块级 `$$...$$`；KaTeX 解析失败时保留可读源码，不出现空白。
- 外链自动加 `target="_blank"` 与 `rel="noopener noreferrer"`。
- 样式覆盖集中在组件 scoped `:deep()` 中，组件样式只消费 `var(--token)`。

## 共享状态组件（FE-012）

- `EmptyState`：标题/描述/主操作，支持 `compact` 紧凑变体。
- `ErrorState`：错误标题、ApiError 消息、错误码与重试事件。
- `LoadingSkeleton`：`list` / `detail` / `card` 三种骨架，列表与详情页已接入。

## 设计系统

- `src/styles/tokens.css`：颜色、字体、间距、圆角、阴影、断点、布局尺寸。
- `src/styles/arco-theme.css`：把 Arco 的 RGB 通道变量（`--arcoblue-1..10` 等）映射到 tokens。
- `src/styles/global.css`：reset、字体、焦点样式、`prefers-reduced-motion`。
- 组件样式只消费 `var(--token)`；原始色值只允许出现在 `tokens.css`。
- 设计来源：`docs/product/04-design-system.md`。

### 视觉方向（2026-11-06 最终：Calm Academic）

- **唯一基准**：`calm-academic/index.html` 的四屏（错题列表 / 录入 / 详情 / 任务中心）。不再做 Studio 混搭。
- **AppShell**：桌面顶部 appbar + 1140px 纸面 frame + 32px 内边距，无侧边栏；移动端 52px appbar + 底部 4 项快捷导航。
- **纸面语言**：白纸/浅灰、1px hairline、8px 卡片圆角、10px frame 圆角、近零阴影、单一 Arco 蓝。
- **字号**：14px UI 下限，15px 控件，16px 题干/正文，18px 面板标题，28px 页面标题。
- **详情**：300px 右侧「处理进度」sticky 栏；原题 / AI 分析 / 相似题为纸张面板；生成题用 01/02/03 大号编号。
- **录入**：1fr + 320px 两栏，题干编辑/预览，右侧题目信息与保存说明，sticky 操作卡。
- **任务中心**：5 列纸面列表，失败行 tinted + 行内错误/重试，筛选不吸顶。

> Arco 组件通过 `unplugin-vue-components` + `ArcoResolver({ sideEffect: true })` 按需自动导入；
> `src/types/components.d.ts` 是自动生成的组件类型声明。新增 Arco 组件后重新运行
> `pnpm dev` / `pnpm build` 即可更新。

## 应用壳

- `src/components/layout/AppShell.vue`：Calm 纸面 frame + 顶部 appbar + 内容区；桌面无侧边栏。
- `src/components/layout/AppTopBar.vue`：品牌（BrandMark + Bababoi + 错题学习机）、错题本 / 录入错题 / 任务中心导航、用户菜单。
- `< 768px`：appbar 收为品牌 + 当前页；底部快捷导航为 错题 / 录入 / 任务 / 练习，内容预留 safe-area。
- 首页 `/` 仍保留占位；统计/设置属于后续 P1，不在主 appbar 中占位。

## 当前目录

```text
src/
├── main.ts              # pinia → mock(dev) → auth restore → router → mount
├── App.vue
├── api/                 # client/errors/types/endpoints + mocks
├── components/
│   ├── ai/              # GenerationProgress（阶段进度/失败重试/停止等待）
│   ├── common/          # PageHeader、MarkdownRenderer、Empty/Error/LoadingSkeleton
│   ├── layout/          # AppShell、AppTopBar、BrandMark、navigation（Calm 顶部 appbar）
│   └── question/        # QuestionCard、AnalysisCard、GeneratedQuestionCard
├── composables/         # useTaskPolling（/tasks 轮询、超时与卸载清理）
├── router/              # 路由表 + 登录守卫 + 标题同步
├── stores/              # pinia 单例 + auth store
├── styles/              # tokens / arco-theme / global
├── types/               # env、RouteMeta 类型扩展
├── utils/               # markdown/KaTeX 渲染、错题标签、日期与任务文案
└── views/               # 登录 + 错题录入/列表/详情 + 任务中心 + 其余占位页
```

除 `/login` 外，AppShell 下的页面都需要登录；未登录访问会跳转到
`/login?redirect=<原路径>`。

## 尚未实现

- FE-013 / FE-014：练习页与统计/概览。
- FE-016 / FE-021：图片上传、裁剪、多题识别与选择生成。
- FE-018：完整键盘/可访问性走查、草稿自动保存/恢复与冲突处理。
- FE-020：选择题/填空题结构编辑器与编辑工具栏。
- FE-017 剩余：练习/统计页的移动端适配（四核心屏已完成 375/1366 适配）。

## 约定

- 使用 `<script setup lang="ts">`；禁止 `as any`、`@ts-ignore`、`@ts-expect-error`。
- 不引入 Tailwind 或第二套 UI 库；优先 Arco 组件。
- API 类型尽量由 `contracts/openapi/openapi.json` 生成，放 `src/api/types.ts`。
- 共享逻辑放 `src/composables/`；共享 UI 放 `src/components/common/`。
- 图片入口：电脑上传 + 手机拍照/相册（两个隐藏 input，拍照加 `capture="environment"`）。

## 相关文档

- 设计 tokens / 组件清单：`docs/product/04-design-system.md`
- 架构与 API：`docs/agent/05-architecture.md`
- 目录职责：`docs/agent/06-file-tree.md`
- 任务清单：`docs/agent/04-todos.md`
