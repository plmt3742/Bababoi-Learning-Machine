# deploy · staging 部署（宿主机 nginx + api 容器）

> 拓扑：浏览器 → 宿主机 nginx（80，静态 dist + `/api` 反代）→ api 容器（127.0.0.1:8000）→ `/srv/bababoi/data`（SQLite + uploads）。
> 暂不签证书、不迁全 compose；11.28 冻结前再看。

```text
/srv/bababoi/
├── repo/     # 源码（无 .git，VERSION 文件记 commit 短 hash）
├── web/      # 前端 dist（nginx root）
├── data/     # bababoi.db(+wal/shm) + uploads/
├── backup/   # 数据库备份
└── .env      # 密钥，chmod 600；不进仓库
```

## 阿里云（国内网络）要额外做的三件事

- **Docker 镜像加速**：控制台「容器镜像服务 → 镜像加速器」拿专属地址，写进 `/etc/docker/daemon.json` 的 `registry-mirrors` 后 `systemctl restart docker`。Dockerfile 用的是 `python:3.13-slim`（Docker Hub），没配加速器大概率拉不动。
- **pip 镜像已在镜像里固定**：`PIP_INDEX_URL` / `UV_DEFAULT_INDEX` 都指向 `mirrors.aliyun.com`；`uv` 不再自己下载 Python（`UV_PYTHON_DOWNLOADS=never`）。
- **安全组只开 80**（有域名后再加 443）。8000 只绑在宿主机 `127.0.0.1`，容器端口映射本身不对外。用 IP 访问不涉及备案；之后绑域名按阿里云要求来。
- 1C2G 的构建如果 OOM，加 1–2G swap 再 `compose build`；前端不在服务器构建，node 的消耗可以忽略。

## 首次部署

1. 宿主机准备（Docker 24+、nginx）：

   ```bash
   sudo mkdir -p /srv/bababoi/{repo,web,data,backup}
   sudo chown -R "$USER" /srv/bababoi
   sudo dnf install -y nginx sqlite   # Alibaba Cloud Linux 3；sqlite 只给宿主机备份用
   ```

2. 传源码（无 `.git`，服务器不能 git clone 时）：

   ```bash
   git archive --format=tar origin/main | gzip | \
     ssh <user>@<IP> "mkdir -p /srv/bababoi/repo && tar -xzf - -C /srv/bababoi/repo"
   ```

   把当前 commit 短 hash 写进 `repo/VERSION`，出问题先看这个文件。

3. 配置环境变量：

   ```bash
   cp /srv/bababoi/repo/deploy/.env.example /srv/bababoi/.env
   chmod 600 /srv/bababoi/.env
   # 填 JWT_SECRET（≥32 字节）、DEMO_PASSWORD、CORS_ORIGINS=["http://<IP>"]
   # TRUSTED_PROXIES=["127.0.0.1"] 保持 JSON 数组
   ```

   `DATABASE_URL` / `UPLOAD_DIR` 由 compose 固定为 `/data` 下，不要在 `.env` 里改。

4. 起后端（entrypoint 会先 `alembic upgrade head` 再 uvicorn，顺序不会反）：

   ```bash
   cd /srv/bababoi/repo
   BABABOI_ENV_FILE=/srv/bababoi/.env docker compose -f deploy/docker-compose.yml up -d --build
   ```

5. 探活：

   ```bash
   curl -s http://127.0.0.1:8000/api/v1/health
   curl -s http://127.0.0.1:8000/api/v1/ready
   # ready 里 checks.llm：mock 阶段是 "mock"，切真 Key 后必须是 "configured"
   ```

6. 前端 build（开发机；`package.json` 没有 packageManager 字段，必须锁 pnpm 9）：

   ```bash
   docker run --rm -v "$PWD/frontend:/app" -w /app node:22-alpine \
     sh -c "npm i -g pnpm@9 && pnpm install --frozen-lockfile && \
            VITE_API_BASE_URL=/api/v1 VITE_USE_MOCK=false pnpm build"
   rsync -a frontend/dist/ <user>@<IP>:/srv/bababoi/web/
   ```

7. nginx（**先清默认站点**：它的 `default_server` 会抢走 IP 访问，页面显示欢迎页而不是前端）：

   ```bash
   sudo rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
   sudo cp /srv/bababoi/repo/deploy/nginx.conf /etc/nginx/conf.d/bababoi.conf
   sudo nginx -t && sudo systemctl enable --now nginx && sudo systemctl reload nginx
   ```

8. 灌种子（首次；`APP_ENV=staging` 才允许）：

   ```bash
   docker compose -f deploy/docker-compose.yml exec api python scripts/seed_demo.py
   # 改口令/答案要重建演示数据：加 --reset --yes
   ```

9. 切真模型（验收前）：`.env` 里 `LLM_MOCK=false` + 填 `LLM_API_KEY`，然后
   `docker compose up -d` 重起，再确认 `/ready` 的 `checks.llm == "configured"`。

## 日常更新

```bash
# 开发机
git archive --format=tar origin/main | gzip | \
  ssh <user>@<IP> "mv /srv/bababoi/repo /srv/bababoi/repo.bak-$(date +%m%d) && \
                   mkdir /srv/bababoi/repo && tar -xzf - -C /srv/bababoi/repo"
# 服务器
cd /srv/bababoi/repo
BABABOI_ENV_FILE=/srv/bababoi/.env docker compose -f deploy/docker-compose.yml up -d --build
```

entrypoint 自动迁移；升级前先按下面备份库。

## 回滚

```bash
cd /srv/bababoi
mv repo repo.bad && mv repo.bak-<MMDD> repo
cd repo && BABABOI_ENV_FILE=/srv/bababoi/.env docker compose -f deploy/docker-compose.yml up -d --build
# 若新版本写过新迁移：换回旧库备份（见下），DB 结构不能只回退代码
```

## 备份（WAL 模式，只拷 .db 会丢最近事务）

```bash
# 宿主机上直接跑（sqlite3 CLI 不再进镜像）
sqlite3 /srv/bababoi/data/bababoi.db ".backup '/srv/bababoi/backup/bababoi-$(date +%Y%m%d-%H%M).db'"
ls -lh /srv/bababoi/backup/
```

上传目录在 `/srv/bababoi/data/uploads`，与库一起备份整个 `data/` 即可。

## 验收

- `http://<IP>/api/v1/health`、`/ready` 200；`ready.checks.db == "ok"`
- 首页能开，`/questions/3` 刷新不 404
- student01 登录；刷新仍在线
- 传一张手机实拍多题图 → ≥4 条；同一张再传一次走缓存（`vision_extract_cache.hit_count` 有值）
- 设置页不 404、统计有数字（说明连真后端）
- 重启容器后登录态与图片都在（验卷）

## 已知取舍

- **只能单进程**：worker 随进程起，多副本会重复消费队列；SQLite 也单写。entrypoint 已固定 `--workers 1`。
- **不加 `--proxy-headers`**：XFF 由 `app/utils/client_ip.py` 解析；`TRUSTED_PROXIES` 是精确字符串匹配，不支持网段。
- **413 不走错误信封**：上传超限由 nginx 直接返回，前端只能给通用文案。
- **SSE 暂无**：`proxy_buffering off` 是给 BE-010 留的口子，当前没有流式接口。
- **VITE_USE_MOCK 生产无效**：`main.ts` 有 `import.meta.env.DEV` 守卫；部署脚本仍显式写 `false`，防有人用 `vite preview` 当部署。
- **mock 期缓存不与真 Key 互通**：缓存键含 model（mock 记 `"mock"`），切真 Key 后第一次识图必慢、第二次才命中。
- **容器以 root 运行**：`/srv/bababoi/data` 里的文件属主是 root，宿主机备份要 sudo；将来改非 root 用户必须先 `chown -R` 数据目录。
- 11.14 前必须有可访问地址；11.28 冻结部署。
