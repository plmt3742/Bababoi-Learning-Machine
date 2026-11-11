# deploy

部署相关文件（目标状态）：

```text
deploy/
├── docker-compose.yml          # 生产/演示：nginx + api + mysql
├── docker-compose.dev.yml      # 本地依赖（MySQL）
├── nginx.conf                  # 静态资源 + /api 反代 + SSE 不缓冲
├── .env.example
├── README.md                   # 部署/回滚步骤
└── scripts/
```

## 约定

- 密钥只放服务器 `.env`；不提交。演示口令由 `DEMO_PASSWORD` 注入（真值只写演示手册），
  每次改种子脚本后 staging 需 `python scripts/seed_demo.py --reset` 重建——
  脚本对已存在的账号「只插不更新」，重跑不会换口令、也不会更新题目答案。
- nginx 的 SSE 路径：`proxy_buffering off; proxy_read_timeout 120s;`。
- MySQL 用 `utf8mb4`；上传目录挂载持久化卷。
- 11.14 前必须有 staging 地址；11.28 冻结部署。
- 回滚步骤写在 `deploy/README.md`。

> 当前还没有 compose/nginx 文件；等 FE-001 / BE-001 脚手架完成后补齐。
