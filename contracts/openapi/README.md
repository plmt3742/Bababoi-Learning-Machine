# openapi

放后端导出的 `openapi.json`。

- 由 FastAPI 自动生成，不要手改。
- 提交仓库，作为前后端契约快照。
- 后端每次改请求/响应 schema，就在同一个 PR 里更新。
- 前端用 `openapi-typescript` 生成 `frontend/src/api/types.ts`。

> 生成命令在 BE-009 / FE-004 里补；当前目录只是占位。
