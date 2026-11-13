# 后端镜像（国内网络优化版）。构建上下文必须是仓库根目录：
#   docker build -f deploy/backend.Dockerfile .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# uv 只用来读 lock 导出确定性清单；lock 里 source 写死 pypi.org，uv sync 会绕开镜像
RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./
# --no-emit-project：lock 里有 source={virtual="."}，不加会把项目自身写进清单，
#   而 backend/pyproject.toml 没有 [build-system]，pip 装不了。
# 只删 index 行，保留 hash：阿里云镜像同步的是 PyPI 原始文件，校验应通过。
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/req.txt \
    && sed -i '/^--index-url /d; /^--extra-index-url /d' /tmp/req.txt \
    && pip install --no-cache-dir -r /tmp/req.txt \
    && rm -f /tmp/req.txt

COPY backend/ ./
COPY deploy/entrypoint.sh /entrypoint.sh

RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

# slim 里没有 wget/curl，直接 python 探活
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
