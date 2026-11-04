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
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── api/            # Axios 实例、端点、类型
│   ├── components/     # layout / question / ai / upload / common
│   ├── composables/    # useAuth / useSSE / useImagePicker
│   ├── router/
│   ├── stores/
│   ├── styles/
│   ├── types/
│   ├── utils/
│   └── views/
├── tests/              # Vitest
└── e2e/                # Playwright
```

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
