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

## ⚠️ 生成物里的 422 不是运行时契约

FastAPI 会自动给带 body 的路由加 `422 HTTPValidationError`。本项目**运行时不是这个形状**：
`app/core/errors.py` 的全局异常处理器把请求校验失败映射成 **400** + 统一信封
`{"detail":{"code","message","request_id"}}`（05 §6.2）；401/403/404/409 也是同一信封，
不逐路由建模。所以：**错误形状以 05 §6.2 为准，生成物里的 422 只当生成器行为**；
前端从快照生成类型时只取 200 的 schema。

## 元数据来源与漂移检查

- title / version / 路径前缀取自 `backend/app/core/meta.py` 的常量；`config.py` 的字段默认值也引用它们——**只有一份真源**，不是脚本里另抄一遍。
- 导出脚本在 import `app` 之前用这三个默认值覆盖环境变量，所以本机 `backend/.env` 里写了 `VERSION`/`API_PREFIX` 也不会污染快照。
- 反过来，**部署环境**若用 `.env` 覆盖这两个值，运行时与快照会分叉：`backend/tests/test_openapi_snapshot.py` 会拦下，需要同步快照或在部署侧固定这两个值。
