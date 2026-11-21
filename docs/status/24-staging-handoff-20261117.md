# 24 · Staging 更新与真接口回归对接单（2026-11-17）

- owner：霹雳马桶（前端）/ 人机（后端）
- status：active
- read_when：演示前更新 staging、切真接口回归、部署排障
- 相关：`deploy/README.md`、`docs/agent/05-architecture.md` §6/§10、`docs/agent/23-backend-handoff-20261113.md`

> **2026-11-17 20:35 复核（重要）**：后端已更新到 `f73d247`（`/health`、`/ready`、新路由 401 正常，BYOK 可用）；但**线上前端 dist 的 `baseURL` 被打成了 `C:/Program Files/Git/api/v1`**（Git Bash 把 `/api/v1` 当路径转换），实测正确地址登录是 401 JSON、错误地址是 405 HTML——线上前端现在登录/调接口全部不可用。
>
> 修复：按 4.2 用 `MSYS_NO_PATHCONV=1`（Git Bash）或 PowerShell/cmd 重新 build，**确认新包的 `baseURL:"/api/v1"`** 后再上传；或者直接用已核对过的 dist：`C:\Users\Administrator\AppData\Local\Temp\opencode\staging-dist-20261117`（entry `index-InLxs-Zs.js`，构建自 main `117b02e`）。

## 0. 先理解三件事（给新手）

1. **staging 是彩排舞台**：一台真服务器 `http://47.107.30.226`，配置和正式环境一样，但不是给用户用的。真手机、真上传、真 AI Key、真数据库，坏了可以修。
2. **代码合到 GitHub 不会自动上舞台**：后端要重新打包容器，前端要重新 build 并把文件传上去，然后自己去点一遍。
3. **这次要上的新东西**：自带 AI Key（#73）、排队任务取消（#74/#75）、前端取消/重新分析/去掉多选 3 道上限（#76）。#77 只改行尾，不影响运行。

## 1. 当前状态

| 项 | 状态 |
|---|---|
| main | `f73d247`（含 #73 / #74 / #75 / #76 / #77） |
| staging | `http://47.107.30.226` 已按本单更新到 `f73d247`（2026-11-17 17:58：镜像重建 + dist 切换，冒烟通过） |
| 数据 | `/srv/bababoi/data/bababoi.db`（SQLite）+ `/srv/bababoi/data/uploads` |
| 新迁移 | #73 带 `e9b1c7f3a2d5`（新表 `user_ai_settings` + `ai_call_logs.key_source`）；entrypoint 会自动跑，**升级前必须备份库** |
| BYOK 密钥 | 已生效：镜像 2026-11-17 重建后 `GET /settings/ai` 200（新账号 `configured=false`） |
| 前端已知缺口 | 识图 `force_refresh` 未接；设置页仍强制重填 Key；503 未按“未启用”降级 |

> CI 最近在 GitHub 侧偶尔卡住（#77 是本地核对后合的）。今天以“本机 checks + 服务器冒烟”为准，但要把 CI 结果补记到 PR/文档。

## 2. 部署前检查（两人一起，约 5 分钟）

> 服务器上的 `/srv/bababoi` 整棵树是 `root:root`，下面涉及该目录的命令统一加 `sudo`。

- [ ] 群里说一声“staging 更新，约 10 分钟”，避开有人正在演示/录屏。
- [ ] **备份数据库**（WAL 模式，必须用 `.backup`，只拷 `.db` 会丢最近事务）：

  ```bash
  sudo sqlite3 /srv/bababoi/data/bababoi.db ".backup '/srv/bababoi/backup/bababoi-$(date +%Y%m%d-%H%M).db'"
  ls -lh /srv/bababoi/backup/
  ```

- [ ] 备份上传目录：

  ```bash
  sudo cp -a /srv/bababoi/data/uploads /srv/bababoi/backup/uploads-$(date +%Y%m%d)
  ```

- [ ] 检查 `.env`（不要整份贴到聊天/日志里）：`JWT_SECRET` ≥32 字节、`CORS_ORIGINS` 与 `TRUSTED_PROXIES` 是 **JSON 数组**、`LLM_MOCK=false`、`LLM_API_KEY`、`SETTINGS_ENCRYPTION_KEY`、`DEMO_PASSWORD`。
- [ ] 磁盘至少留 1G：`df -h /srv`。
- [ ] 记下当前版本：`sudo cat /srv/bababoi/repo/VERSION`（回滚时对得上；`/srv/bababoi` 整棵树是 root:root，不加 sudo 会 Permission denied）。

## 3. 后端更新（人机）

按 `deploy/README.md` 的「日常更新」走：

```bash
# 开发机 / 能 ssh 的人
git archive --format=tar origin/main | gzip | \
  ssh <user>@47.107.30.226 \
  "mv /srv/bababoi/repo /srv/bababoi/repo.bak-$(date +%m%d-%H%M) && \
   mkdir /srv/bababoi/repo && tar -xzf - -C /srv/bababoi/repo"

# 服务器
cd /srv/bababoi/repo
echo f73d247 > VERSION
BABABOI_ENV_FILE=/srv/bababoi/.env \
  docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f api
```

**验证（后端自己先过一遍）：**

- [ ] `curl -s http://127.0.0.1:8000/api/v1/health` → 200；`/ready` → `checks.db == "ok"`、`checks.llm == "configured"`。
- [ ] `docker compose exec api alembic current` → `e9b1c7f3a2d5 (head)`；镜像里**没有** sqlite3 CLI（`deploy/README.md` 已写明），表用宿主机查：`sudo sqlite3 /srv/bababoi/data/bababoi.db ".tables"`，能看到 `user_ai_settings`。
- [ ] 带 token 请求 `/api/v1/settings/ai` → 200（不是 404）；新账号 `configured=false`。
- [ ] 不带 token 请求 `/api/v1/tasks/1/cancel` → 401（说明路由存在）；带 token 对 running 任务 → 400。
- [ ] 日志没有 traceback；`docker compose ps` 里 api 是 Up。

**注意：**

- 不要 `docker compose down -v`，会删数据卷。
- 不要顺手跑 `seed_demo.py --reset --yes`，那会重建演示数据；除非明确要重置。
- `SETTINGS_ENCRYPTION_KEY` 与数据同寿命：换 Key 前先清空 `user_ai_settings`，否则已存密文全部解不开。这次只是补上，不要换。

## 4. 前端更新（霹雳马桶）

### 4.1 本机检查（必须全绿）

```bash
git fetch origin main
git checkout f73d247
cd frontend
pnpm install --frozen-lockfile
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

### 4.2 用真实后端参数重新 build

Windows PowerShell：

```powershell
cd frontend
$env:VITE_API_BASE_URL="/api/v1"
$env:VITE_USE_MOCK="false"
pnpm build
```

cmd（注意等号两边不要留空格）：

```bat
cd frontend
set "VITE_API_BASE_URL=/api/v1"
set "VITE_USE_MOCK=false"
pnpm build
```

> 也可以按 `deploy/README.md` 用 `node:22-alpine + pnpm@9` 的 Docker 命令构建；服务器上不装 Node，前端只在开发机构建。

### 4.3 上传（先传到 `web.new`，再原子切换）

```bash
# 服务器先清空目录（固定路径，不用 glob：手误把 web.new 打成 web 就会删线上前端）
ssh <user>@47.107.30.226 "rm -rf /srv/bababoi/web.new && mkdir -p /srv/bababoi/web.new"

# 本机（Git Bash / WSL）
rsync -a --delete frontend/dist/ <user>@47.107.30.226:/srv/bababoi/web.new/

# 或在 Windows PowerShell 里
scp -r .\frontend\dist\. <user>@47.107.30.226:/srv/bababoi/web.new/
```

切换（有 1–2 秒空窗，可接受）：

```bash
ssh <user>@47.107.30.226 \
  "cd /srv/bababoi && mv web web.bak-$(date +%m%d-%H%M) && mv web.new web"
```

**验证：**

- [ ] `curl -I http://47.107.30.226/` → 200，`Cache-Control: no-cache`（index.html）。
- [ ] `curl -I http://47.107.30.226/assets/<某个hash文件>` → `immutable`。
- [ ] 浏览器硬刷新（Ctrl+F5）或无痕窗口，任务中心能看到「已取消」筛选、详情页能看到「重新分析」。
- [ ] 直接访问 `/questions/1` 刷新不 404（SPA 回退正常）。

## 5. 真接口回归清单（前端主责，后端配合）

用演示账号（`student01`，口令见演示手册）在 **桌面 1366** 走一遍，再在 **手机 4G** 走核心页。

| # | 操作 | 预期 |
|---|---|---|
| 1 | 打开首页 | 欢迎页不是 nginx 默认页；统计/最近错题/任务有真实数据 |
| 2 | 登录 → 刷新页面 | 仍在登录态；错误口令提示清楚 |
| 3 | 录入一道文本错题 | 保存成功；分析任务从排队→生成中→完成；答案/解析自动补全 |
| 4 | 图片录入：上传/裁剪/识别 | ≥4 条可编辑条目；保存后每道题都有分析任务 |
| 5 | 同一张图再识别一次 | 很快返回（缓存命中）；前端暂时不显示“缓存”，属已知缺口 |
| 6 | 生成相似题 | 3 段任务进队列；任务中心按题折叠；详情页 3 张卡 |
| 7 | 取消一个排队中的生成段 | 行变「已取消」；计数变化；该段出现「重新生成该段」；另外两段不受影响 |
| 8 | 任务中心取消分析任务 → 回详情 | 显示「分析已取消」+「重新分析」；点重新分析能重新跑完 |
| 9 | 图片保存后勾选 4 道以上生成 | 前端不再拦 3 道；任务按并发排队；可以取消其中几道 |
| 10 | 任务失败重试（如果出现） | 失败卡有错误码/原因；单段重试不覆盖其它段 |
| 11 | 做一道练习并提交 | 记录成功；统计页正确率/练习数变化 |
| 12 | 设置页：配置 BYOK（测试 Key 用你自己的 OpenAI/DeepSeek Key，或找 人机 要一次性 Key；不要贴群/仓库） | 返回掩码；刷新后仍在；删除后回退系统 Key；响应/页面无明文 Key |
| 13 | 设置页：生成偏好开关 | 关闭后刷新仍生效；生成时按新设置执行 |
| 14 | 手机 4G：登录 / 图片 / 详情 / 任务中心 | 375 不横向溢出；相机/相册能选图；图片按钮可用 |
| 15 | 错误态：断网 / 大图 / 错 Key | 断网有错误提示；>10MB 图有提示（413 由 nginx 直接返回，文案可能较通用）；错 Key 返回 AI 错误而不是白屏 |

**BYOK 额外核对（后端）：**

```bash
# 库里有行、只有密文 + last4，没有明文
sudo sqlite3 /srv/bababoi/data/bababoi.db \
  "select user_id, provider, key_last4, length(api_key_ciphertext) from user_ai_settings;"

# 用用户 Key 跑过一次生成后，日志来源应为 user
sudo sqlite3 /srv/bababoi/data/bababoi.db \
  "select id, operation, key_source, status from ai_call_logs order by id desc limit 5;"
```

## 6. 验收清单

- [ ] API 镜像是 `f73d247`；`/settings/ai` 200；`user_ai_settings` 表存在。
- [ ] 前端 dist 含：任务中心「已取消」筛选、排队「取消排队」、详情「重新分析」、多选不再拦 3 道。
- [ ] 桌面 15 步全过；手机 4G 核心页可用。
- [ ] BYOK 配/删/回退都正常；响应、localStorage、日志无明文 Key。
- [ ] 重启容器后登录态、上传图片、数据库记录都在（验卷）。
- [ ] 备份文件存在；回滚步骤至少演练“只回前端”一次。
- [ ] 回归问题有记录：现象 / 负责人 / 状态。

## 7. 回滚

**只回前端（最快，1 分钟）：**

```bash
ssh <user>@47.107.30.226 \
  "cd /srv/bababoi && mv web web.bad-$(date +%m%d-%H%M) && mv web.bak-<MMDD-HHMM> web"
```

**回后端：**

```bash
cd /srv/bababoi
mv repo repo.bad-$(date +%m%d-%H%M) && mv repo.bak-<MMDD-HHMM> repo
cd repo && BABABOI_ENV_FILE=/srv/bababoi/.env \
  docker compose -f deploy/docker-compose.yml up -d --build
```

**如果迁移/数据出问题：**

> 顺序必须是 **停 → 删 WAL/SHM → 拷 → 起**。SQLite 打开库文件时会把目录里残留的 `-wal` 重放上去，先拷库不删 WAL 会把刚恢复的备份立刻污染回旧数据。

1. 停容器：`docker compose -f deploy/docker-compose.yml stop api`
2. 删残留 WAL/SHM：

   ```bash
   sudo rm -f /srv/bababoi/data/bababoi.db-wal /srv/bababoi/data/bababoi.db-shm
   ```

3. 用备份替换库：

   ```bash
   sudo cp -a /srv/bababoi/backup/bababoi-YYYYMMDD-HHMM.db /srv/bababoi/data/bababoi.db
   ```

4. 起容器：`docker compose ... up -d`
5. 本批只有 #73 一个新迁移（新增表/列），旧代码遇到新表通常无害；但“只回代码不回库”要先确认。

## 8. 已知问题 / 这次不做

- **识图 `force_refresh` 前端未接**：同一张图“重试”会命中缓存；不会是这次部署的阻塞项。
- **BYOK 保存仍强制重填 Key**：后端已支持省略（保留原 Key），前端待改。
- **503 未按“未启用”降级**：服务端缺加密密钥时，设置页显示普通错误。
- **SSE 没有**：当前用 `GET /tasks` 轮询，够用。
- **admin 管理端**：P1，不在 11.29 演示路径。
- **HTTPS/域名没有**：现在是纯 IP/HTTP；手机拍照用 `<input capture>` 可以工作，但如果以后改 `getUserMedia` 就必须 HTTPS。
- **413 是 nginx 直接返回**：不走统一错误信封，前端只能给通用文案。
- **单进程/SQLite**：容器固定 `--workers 1`；不要多副本。

## 9. 分工与时间

| 时间 | 事项 | 谁 |
|---|---|---|
| 11.17 | 备份 → 后端重建镜像 → 前端 build/上传 → 桌面回归 | 人机 + 霹雳马桶 |
| 11.18 | 手机 4G + 375 回归；修回归问题 | 霹雳马桶 |
| 11.19–11.21 | 只做 P1 小项（识图重识别、BYOK 保存体验）+ 演示准备 | 两人 |
| 11.22 | **功能冻结**，之后只修 P0/P1 | 两人 |
| 11.24 | 种子数据/账号/数据清理 | 人机 |
| 11.26 / 11.28 / 11.29 | 彩排；备用录屏/截图；正式演示 | 两人 |

> 两个“冻结”不是同一件事：这里的 **11.22 是功能冻结**（不再加新功能），`deploy/README.md` 的 **11.28 是部署冻结**（不再改部署配置）。

## 10. 排障速查

| 现象 | 多半是 | 处理 |
|---|---|---|
| 打开是 nginx 欢迎页 | 默认站点抢了 80 | 删 `/etc/nginx/conf.d/default.conf` / `sites-enabled/default`，reload |
| `/settings/ai` 404 | API 镜像还是旧的 | 重新 `up -d --build`，确认 `VERSION` |
| PUT `/settings/ai` 503 | `SETTINGS_ENCRYPTION_KEY` 缺失/非法 | 补 Key；非法时进程启动就会报错 |
| 全站 401 / CORS 报错 | `.env` 的 `CORS_ORIGINS` 不是 JSON 数组或域名不符 | 改成 `["http://47.107.30.226"]` 后重启 |
| 上传 413 | nginx `client_max_body_size` 太小 | 确认 `deploy/nginx.conf` 的 12m 生效 |
| 502 | api 容器没起/端口错 | `docker compose ps`、`logs -f api` |
| 图片 404 | `UPLOAD_DIR` 挂载/权限 | 看 `/srv/bababoi/data/uploads` 与容器内 `/data/uploads` |
| 时间差 8 小时 | 前端把 naive UTC 当本地时间 | 确认走 `utils/time.ts` 的 `parseApiTime` |
| 识图慢/截断 | 180s 超时、24000 token 上限；不是缓存问题 | 看 `ai_call_logs` 的 latency/finish_reason |
| 同一张图很快 | 缓存命中（预期） | 目前没有“强制重跑”按钮，属已知缺口 |
| 任务一直 running | worker 异常/旧任务 | 看 api 日志；重启会重置 running→queued，但要查原因 |

> 重启救回几条任务不用手工查库：`docker compose -f deploy/docker-compose.yml logs api | grep 卡在 running` 能看到每次启动把多少条 running 放回队列（`main.py` lifespan 里的 `reset_stale_running`）。

## 11. 链接

- 部署细节：`deploy/README.md`
- 接口契约：`docs/agent/05-architecture.md` §6、§10
- 后端交接：`docs/agent/23-backend-handoff-20261113.md`
- 相关 PR：#72（部署脚手架）、#73（BYOK）、#74/#75（任务取消）、#76（前端取消/重新分析/去上限）、#77（行尾）
