# frontend/src/api

HTTP 客户端与接口类型。

## 文件

```text
api/
├── client.ts        # Axios 实例、baseURL、token、401、错误归一化
├── auth.ts          # /auth/*
├── questions.ts     # /questions/*
├── practice.ts      # /practice-records
├── stats.ts         # /stats/*
├── settings.ts      # /settings/ai、/settings/preferences
├── uploads.ts       # /uploads/*、/questions/from-image
├── drafts.ts        # /drafts/me
├── types.ts         # 由 contracts/openapi 生成（或手写对照）
└── mocks/           # axios-mock-adapter（仅 dev）
```

## 规则

1. 所有请求走 `client.ts`；不要在组件里直接 `fetch`/`axios`。
2. 401 统一清 token、跳登录；不要让每个页面自己处理。
3. 错误按 `detail.code` 分支；不要匹配 message。
4. SSE 用 `fetch` + `ReadableStream`，不用 Axios。
5. 字段以 `docs/agent/05-architecture.md` / OpenAPI 为准；不自己发明。
6. 不在前端存 LLM Key；`VITE_` 变量只放 API 基地址。
7. Mock 字段必须与 `contracts/examples/` 一致。

## 相关

- 契约：`contracts/README.md`
- API 文档：`docs/agent/05-architecture.md` 第 6 节
