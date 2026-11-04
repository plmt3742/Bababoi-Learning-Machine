# frontend

Vue 3 + Vite + TypeScript + Arco Design Vue。

> 状态：目录骨架。脚手架任务 `FE-001`，见 `docs/agent/04-todos.md`。

## 计划结构

```text
frontend/
├── package.json
├── pnpm-lock.yaml
├── vite.config.ts
├── tsconfig.json
├── index.html
├── .env.example
├── public/                 # 静态资源（favicon 等）
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── api/                # Axios 实例、端点、types（OpenAPI 生成）
│   ├── assets/             # 图片/字体
│   ├── components/
│   │   ├── common/         # 共享 UI：PageHeader/Empty/Error/Loading/Markdown/Tag...
│   │   ├── layout/         # AppShell/Sidebar/TopBar
│   │   ├── question/       # QuestionCard/QuestionForm/QuestionDetail
│   │   ├── ai/             # AIGenerationPanel/StageProgress/GeneratedQuestionCard
│   │   └── upload/         # ImageInput/ImagePreview/MobileImagePicker
│   ├── composables/        # useAuth/useSSE/useImagePicker/usePagination
│   ├── router/
│   ├── stores/
│   ├── styles/             # tokens.css / arco.css / global.css
│   ├── types/
│   ├── utils/
│   └── views/
├── tests/                  # Vitest
└── e2e/                    # Playwright
```

## 共享组件

- 通用 UI 放 `src/components/common/`；规则见 `src/components/common/README.md`。
- 业务组件按领域放 `question/`、`ai/`、`upload/`；不要都塞进 `common/`。
- API 类型从 `contracts/openapi/openapi.json` 生成，放 `src/api/types.ts`。
- 共享逻辑放 `src/composables/`；共享样式变量放 `src/styles/tokens.css`。

## 约定

- 用 TypeScript；API 类型尽量由 OpenAPI 生成。
- Arco 组件优先；缺 Chat/Markdown/Charts，需自建或接第三方。
- 图片入口：电脑上传；手机拍照/相册（两个隐藏 input，拍照加 `capture="environment"`）。
- 不引入 Tailwind 与 Arco reset 混用；如必须，先处理冲突。

## 完成后命令

```bash
pnpm install
pnpm dev
pnpm build
pnpm test
```
