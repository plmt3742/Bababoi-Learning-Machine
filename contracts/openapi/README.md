# openapi

放后端导出的 `openapi.json`。

- 由 FastAPI 自动生成，不要手改。
- 提交仓库，作为前后端契约快照。
- 后端每次改请求/响应 schema，就在同一个 PR 里更新。
- 前端用 `openapi-typescript` 生成 `frontend/src/api/types.ts`。

生成命令（BE-009 起）：

```bash
cd backend
uv run python scripts/export_openapi.py          # 重新导出并覆盖本目录的 openapi.json
uv run python scripts/export_openapi.py --check  # 只比对不写；CI 的 backend job 跑这个
```

输出是确定性的（键排序 + 2 空格缩进 + LF），CI 比对失败说明改了 schema 却没更新快照。
