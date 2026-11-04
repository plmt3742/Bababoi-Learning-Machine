# scripts

跨前后端的开发脚本，只放“两边都要用”的东西。

## 可以放

- 导出 OpenAPI：`export-openapi.ps1` / `export-openapi.sh`
- 一键检查：lint + typecheck + test + build
- 本地依赖启动/停止（Docker Compose）
- 种子数据导入（调用 backend/scripts）
- 文档链接检查

## 不要放

- 业务逻辑（放 frontend/backend）
- 密钥、真实数据
- 只属于某一端的脚本（放 `frontend/package.json` 或 `backend/scripts/`）

## 约定

- Windows 优先 `.ps1`；跨平台再补 `.sh`。
- 脚本里不写死绝对路径；用 `$PSScriptRoot` / `git rev-parse --show-toplevel`。
- 运行前打印“要做什么”，失败给明确错误。
- 不提交 `.env`；读环境变量。

> 当前是目录骨架，脚本在 FE-001 / BE-009 / OPS-001 里补。
