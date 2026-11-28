# 25 · 前端任务单（2026-11-17）

- owner：霹雳马桶（前端）/ 人机（后端配合）
- status：active
- read_when：前端排期、演示前收口、staging 真接口回归后
- 相关：`24-staging-handoff-20261117.md`、`05-architecture.md` §6.4/§6.8/§6.9、`04-todos.md` FE-036/FE-037

## 0. 现在的事实（别再按旧口径做）

- main `117b02e`，staging 已更新到 `f73d247`（2026-11-17 17:58）：**排队取消、重新分析、多选不再拦 3 道、BYOK** 都已上线，冒烟通过。
- 后端能力边界：`POST /tasks/{id}/cancel` 只认 `queued`；`running` 不可打断（返回 400）；取消会清空 `error_code`/`error_message`，状态变 `canceled`；同一段可以立即重新生成。
- BYOK：`PUT /settings/ai` 的 `api_key` **可省略 = 保留已存 Key**；切换 provider 必须重填；清空请走 `DELETE`。
- 识图：`POST /questions/from-image` 支持 `force_refresh=true`（60s 冷却，冷区内 429 `VISION_REFRESH_COOLDOWN`）；响应带 `cached` / `extracted_at`。
- 不在演示路径：admin（P1）、SSE、HTTPS/域名。

## 1. 任务清单（按优先级）

| # | 任务 | 为什么现在做 | 验收（可核对） |
|---|---|---|---|
| F1 | 识图「重新识别」入口接 `force_refresh` | 后端已就绪，前端未接：同一张图重试会命中缓存，用户以为没重新识别（24 号单 §8 已知缺口） | 确认页有「重新识别」；请求带 `{force_refresh:true}`；60s 内再点显示 429 文案；成功后旧结果被覆盖、`extracted_at` 更新 |
| F2 | BYOK 保存不再强制重填 Key | 后端省略 `api_key` = 保留；前端 `utils/settings.ts` 仍要求必填，改 model 也要重粘（24 号单 §8） | 已配置时只改 model/base_url 可直接保存；切 provider 仍要求填 Key；空提交不会清 Key；清空只能走「删除」 |
| F3 | 503 按“未启用”降级 | 服务端缺/坏 `SETTINGS_ENCRYPTION_KEY` 时 **`PUT /settings/ai`** 返回 503 `AI_PROVIDER_ERROR`（文案「个人 API Key 暂不可用，请稍后再试」）；`GET` 不解密，保持 200（2026-11-28 #128 定案，原「PUT/GET」收窄为仅 PUT） | 503 时 AI 面板显示降级块并保留账号信息/生成偏好区，不把整页判错 |
| F4 | 图片录入页生成后的页内进度 | 4 道题 = 12 个任务，现在只显示「已创建任务」，必须跳任务中心才知道进度 | 保存面板里每题显示 3 段状态（排队/生成中/完成/已取消），排队段有「取消排队」；或至少给「去任务中心」深链并带题号 |
| F5 | 上传超限/网络错误文案 | 413 由 nginx 直接返回（非统一信封），前端只能给通用提示 | 超过大小上限时提示「图片太大，请压缩或裁剪后重试」；断网有重试入口，不白屏 |
| F6 | 图片确认页题干 LaTeX 预览 | 编辑器里能写公式，但确认卡片看不到渲染效果，容易带着坏公式入库（此前的任务卡） | `ImageItemCard` 题干区可切换渲染预览；KaTeX 报错时保留原文、不丢内容 |
| F7 | 24 号单 §5 的 15 步回归（桌面 1366 + 手机 4G） | 这次更新动了任务状态机和前端队列 UI，必须真机走一遍 | 每步结果记入 24 号单或 issue；失败项带「现象 / 负责人 / 状态」，P0 当场修，P1 记入本单 |

## 2. 口径提醒（容易再踩）

- 「三段并发」是**每道题 3 段**；多选不再有 3 道上限，超出按 `task_max_concurrency=6` 排队。
- `canceled` 是终止态：不能 `retry`，只能「重新生成该段」或「重新分析」；错误字段已清空，别拿旧 `error_code` 显示。
- 设置页的掩码由服务端给（`sk-****abcd` / `****1234`），前端不要自己拼 `sk-` 前缀。
- 任务中心的 `canceled` 筛选和后端 `GET /tasks?status=canceled` 一致，别再在本地过滤状态字符串。

## 3. 不做 / 后置

- admin 管理台（P1，ADR-005）、SSE、HTTPS/域名、单题重生成（P1）、自研图片组。

## 4. 验证入口

- staging：`http://47.107.30.226`（`student01`，口令见演示手册）
- 接口自测：`POST /tasks/{id}/cancel`、`GET /tasks?status=canceled`、`GET/PUT/DELETE /settings/ai`、`POST /questions/from-image`（带 `force_refresh`）
- 已知非 bug：缓存命中时页面没有「缓存」标识；413 文案通用；识图强刷有 60s 冷却。
