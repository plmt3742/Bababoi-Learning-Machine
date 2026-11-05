# frontend

Vue 3 + Vite + TypeScript + Arco Design Vue。

> 状态：FE-001 ~ FE-006 已完成（2026-11-05）。应用壳、路由、设计 tokens、API client、
> Mock API、登录/注册与路由守卫已就位；业务页面目前仍是占位页。

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
- Mock 覆盖：认证、错题 CRUD/筛选、任务列表与重试、草稿 GET/PUT/DELETE、
  练习记录创建/列表。Mock 数据在内存中，刷新后新增数据会重置（演示账号保留）。

## 路由

使用 `createWebHistory`，每个路由通过 `meta.title` 同步浏览器标题。

| 路径             | 页面                  | 布局     |
| ---------------- | --------------------- | -------- |
| `/login`         | 登录/注册             | 独立页   |
| `/`              | 首页占位              | AppShell |
| `/questions`     | 错题本占位            | AppShell |
| `/questions/new` | 录入错题占位          | AppShell |
| `/tasks`         | 任务中心占位          | AppShell |
| `/questions/:id` | 错题详情占位          | AppShell |
| `/practice/:id?` | 练习占位（`id` 可选） | AppShell |
| `/stats`         | 统计占位（P1）        | AppShell |
| 其余路径         | 404                   | AppShell |

## 设计系统

- `src/styles/tokens.css`：颜色、字体、间距、圆角、阴影、断点、布局尺寸。
- `src/styles/arco-theme.css`：把 Arco 的 RGB 通道变量（`--arcoblue-1..10` 等）映射到 tokens。
- `src/styles/global.css`：reset、字体、焦点样式、`prefers-reduced-motion`。
- 组件样式只消费 `var(--token)`；原始色值只允许出现在 `tokens.css`。
- 设计来源：`docs/product/04-design-system.md`。

> Arco 组件通过 `unplugin-vue-components` + `ArcoResolver({ sideEffect: true })` 按需自动导入；
> `src/types/components.d.ts` 是自动生成的组件类型声明。新增 Arco 组件后重新运行
> `pnpm dev` / `pnpm build` 即可更新。

## 应用壳

- `src/components/layout/AppShell.vue`：桌面侧边栏 + 顶栏 + 内容区。
- `< 1200px`：侧边栏收起为左侧 Drawer。
- `< 768px`：增加底部快捷导航（首页/错题本/任务中心/练习），内容预留 safe-area。
- 导航项：首页、错题本、任务中心、练习、统计（P1）、设置（P1，暂为禁用占位）。

## 当前目录

```text
src/
├── main.ts              # pinia → mock(dev) → auth restore → router → mount
├── App.vue
├── api/                 # client/errors/types/endpoints + mocks
├── components/
│   ├── common/          # PageHeader、PlaceholderPanel
│   └── layout/          # AppShell、AppSidebar、AppTopBar、AppNavigation
├── router/              # 路由表 + 登录守卫 + 标题同步
├── stores/              # pinia 单例 + auth store
├── styles/              # tokens / arco-theme / global
├── types/               # env、RouteMeta 类型扩展
└── views/               # 登录/注册 + 8 个占位业务页面
```

除 `/login` 外，AppShell 下的页面都需要登录；未登录访问会跳转到
`/login?redirect=<原路径>`。

## 尚未实现

- FE-007 及以后：录入、列表/详情、AI 生成、练习、统计等业务页面（API 层与 Mock
  已按 P0 契约准备好）。
- 图片上传/裁剪/多题识别（FE-016 / FE-021）。

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
