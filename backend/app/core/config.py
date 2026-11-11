"""应用配置：环境变量 / .env 集中管理，PRD 里那些 🔵 数值定稿后只改这里。"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    project_name: str = "Bababoi Learning Machine"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # 运行环境：development / local / staging / production。
    # scripts/seed_demo.py 用它做危险操作守卫（production 拒绝运行；--reset 需 --yes）
    app_env: str = "development"
    # 演示账号口令：只给 seed_demo.py 用，必须由 .env / 环境变量注入，代码里不给默认值
    demo_password: str = ""

    # CORS：只列允许的来源，不用 *（05 §9.4）
    cors_origins: list[str] = ["http://localhost:5173"]

    # FR-7 账号：JWT 有效期 7 天（05 §6.3）；secret 必须由环境变量注入
    jwt_secret: str = ""
    access_token_expire_days: int = 7
    # 登录失败限流（05 §6.3：5 次/分钟/IP，内存计数即可，不引入 Redis）
    login_rate_limit: int = 5
    login_rate_window_s: int = 60
    # 反代后 request.client.host 恒为 nginx 的 IP，限流会把所有用户算成同一个（13号 §4.6）。
    # 只有直连来源在这个列表里时，才读 X-Forwarded-For；默认空 = 不信任任何代理头。
    trusted_proxies: list[str] = []

    # 数据库：BE-001 只提供配置项，连接与建表在 BE-002
    database_url: str = ""

    # LLM（ADR-003：DeepSeek deepseek-flash，OpenAI 兼容接口）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-flash"
    llm_mock: bool = True  # CI 与本地默认不调真实模型（12号 §6.1）
    # 识图是否让模型先"想一遍"。实测（两张实拍整页，生产提示词+生产校验器）：
    #   开思考 28.9s / 5861 输出 token（其中 reasoning 14617 字符），5 条
    #   关思考  3.4s /  714 输出 token，同样 5 条，题干字数 393 vs 405，过严格校验数相同
    # 密页横拍那张关思考反而多认出一条（4 vs 3）。抄题这种活不需要推理，
    # 思考的 token 还会顶满 max_tokens 变成"截断"，所以默认关掉。
    # 留成配置而不是写死：样本只有两张图，演示前如果发现某类题（手写/复杂排版）掉质量，
    # 改一个环境变量就能切回来，不用发版。
    vision_thinking: bool = False

    # 超时与队列（PRD 5.4 / 5.6，12号 §3.3）
    recognize_client_timeout_s: int = 90  # 前端等待上限
    task_hard_timeout_s: int = 120  # 单任务服务端硬超时
    # ADR-006：一次生题排 3 段，2 个并发位会让第 3 段干等一轮；实测 3 段同瞬间并发无 429，
    # 所以默认给 6（两段满速）。生产仍要看 RPM/TPM 监控再调。
    task_max_concurrency: int = 6
    task_retry_limit: int = 1
    # 自动重排队的时间上限：一段跑了 90s 还没出结果，再排一次只会让用户更久看不到终态，
    # 直接置 failed 让前端出"重试"卡（14 号 D8）。
    task_requeue_deadline_s: int = 90
    task_workers_enabled: bool = True  # API 测试里关掉，worker 单测直接调同步函数

    # 图片（12号 §5；上传兜底 10MB，落库前压到 5MB/2000px）
    upload_dir: str = "./uploads"
    image_max_upload_bytes: int = 10 * 1024 * 1024
    image_max_stored_bytes: int = 5 * 1024 * 1024
    image_max_edge_px: int = 2000
    # 送多模态模型前的临时缩放（14 号 §5-3 实测：长边压到 1200 后 token/延迟明显下降、
    # 质量不掉）。只在内存里做，不落第二份文件。
    image_llm_max_edge_px: int = 1200
    image_allowed_types: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # 分页（05 §6.1）
    page_size_default: int = 20
    page_size_max: int = 100

    def validate_for_startup(self) -> None:
        """启动时把密钥类配置一次性查完，而不是等第一个请求 500（13号 §4 / issue #11）。"""
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError(
                "JWT_SECRET 未配置或不足 32 字节（05 §9.4）；"
                "生成：python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if not self.llm_mock and not self.llm_api_key:
            raise RuntimeError("LLM_MOCK=false 但 LLM_API_KEY 未配置")


settings = Settings()
