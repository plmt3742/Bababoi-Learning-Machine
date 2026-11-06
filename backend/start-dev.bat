@echo off
REM 本地开发一键启动：只用 SQLite，不需要 Docker
REM   start-dev.bat          = mock 模式（不需要 API Key，链路和校验照跑）
REM   start-dev.bat real     = 真模型（读 backend\.env 里的 LLM_API_KEY，会实际计费）
REM 环境变量优先级高于 .env，所以这里只在不带 real 时强制 mock
cd /d "%~dp0"
set "JWT_SECRET=dev-secret-0123456789abcdef0123456789abcdef"
if /I "%~1"=="real" (
  set "LLM_MOCK="
  echo   LLM 模式：真实 deepseek-flash（读 backend\.env 的 LLM_API_KEY）
) else (
  set "LLM_MOCK=true"
  echo   LLM 模式：mock（不花钱；要跑真模型用 start-dev.bat real）
)
echo.
echo   Bababoi backend dev server
echo   测试台  http://127.0.0.1:8000/static/test-console.html
echo   API 文档 http://127.0.0.1:8000/docs
echo   Ctrl+C 停止
echo.
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
