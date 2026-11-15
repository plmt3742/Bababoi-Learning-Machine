#!/bin/sh
# 迁移必须早于服务启动：表不存在时缓存读写会被 except 兜底吞成 warning，
# 功能不报错但缓存静默失效（演示时"怎么不秒回"才发现）。
set -eu

python -m alembic upgrade head

# 只能单进程：worker 线程随进程在 lifespan 里起，多进程会重复消费同一队列；
# SQLite 也是单写。不要加 --proxy-headers，XFF 由 app/utils/client_ip.py 解析。
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
