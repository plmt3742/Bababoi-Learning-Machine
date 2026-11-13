# 后端镜像：uv 依赖 + 单进程 uvicorn。构建上下文必须是仓库根目录：
#   docker build -f deploy/backend.Dockerfile .
# 用 Docker Hub 的 python 镜像（国内可配阿里云加速器），不走 ghcr.io。
FROM python:3.13-slim

# 国内网络：pypi 走阿里云镜像；uv 不再自己下载 Python（镜像里已经是 3.13）
ENV PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/ \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir "uv>=0.8,<1"

WORKDIR /app

# 先装依赖再拷代码：改业务代码不会打掉依赖层
COPY backend/pyproject.toml backend/uv.lock ./
# uv.lock 里 source 固定写成 pypi.org，uv sync 会无视 UV_DEFAULT_INDEX 去慢慢拉；
# 这里只用 uv 从 lock 导出确定性清单，真正下载交给 pip 走阿里云镜像。
RUN uv export --frozen --no-dev --no-hashes --format requirements-txt -o /tmp/requirements.txt \
    && sed -i '/^--/d' /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/ ./
COPY deploy/entrypoint.sh /entrypoint.sh

# sqlite3 CLI 只给备份/排查用（slim 镜像默认没有）
RUN apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && chmod +x /entrypoint.sh

EXPOSE 8000

# 不用 wget/curl（slim 里都没有），直接 python 探活
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
