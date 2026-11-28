"""应用配置：环境变量 / .env 集中管理，PRD 里那些 🔵 数值定稿后只改这里。"""
from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.meta import API_PREFIX, PROJECT_NAME, VERSION

# 识图第二跳（结构化）最坏耗时与安全垫：单次调用上限必须给它们留出预算。
# 30 取结构化跳的实测上界（05 §6.8：两跳合计 17–60s、密页转录单跳 90.2s；
# 结构化单跳没有单独的分位记录，换模型/加长输出必须重测）。
STRUCTURE_WORST_CASE_S = 30
SAFETY_MARGIN_S = 5
# 整单 deadline 与前端轮询上限 180s（实际排队 40 + 140）配套，单独调大会让前端提前放弃
VISION_RUN_DEADLINE_MAX_S = 140


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 默认值取自 app/core/meta.py，与导出脚本共用同一份（不写字面量两次）
    project_name: str = PROJECT_NAME
    version: str = VERSION
    api_prefix: str = API_PREFIX

    # 运行环境：development / local / staging / production。
    # scripts/seed_demo.py 用它做危险操作守卫（production 拒绝运行；--reset 需 --yes）
    app_env: str = "development"
    # 演示账号口令：只给 seed_demo.py 用，必须由 .env / 环境变量注入，代码里不给默认值
    demo_password: str = ""

    # CORS：只列允许的来源，不用 *（05 §9.4）。
    # 5174 是 admin/ 的 Vite 开发端口（ADR-009）；开发期 admin 走 Vite 代理，这里
    # 保留直连来源，免得调试时因为一个 IP/localhost 写法差异被拦。
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # FR-7 账号：JWT 有效期 7 天（05 §6.3）；secret 必须由环境变量注入
    jwt_secret: str = ""
    access_token_expire_days: int = 7
    # ADM-002：管理员 token 单独 8h（交接单 §12 待确认项 1 的默认值）。
    # 同一签名密钥与 token_version 校验链，只是签发时 exp 更短。
    admin_token_expire_hours: int = 8
    # 登录失败限流（05 §6.3）：5 次/分钟/IP；存储由下面的 rate_limit_storage_url 决定
    login_rate_limit: int = 5
    login_rate_window_s: int = 60
    # 注册按 IP 限额：注册是零成本的，不挡的话"换号"就能绕过按用户的 AI 额度。
    # 默认 30/小时：实验室考核全班通常一个 NAT 出口，3/小时会把正常注册挡在外面；
    # 公开部署想收紧就调小（或被邀请码取代）。
    register_rate_limit: int = 30
    register_rate_window_s: int = 3600
    # 限流存储（limits URI）：单实例默认进程内存；多实例改 redis://host:6379/0
    #（需安装 limits[redis]），业务代码不用改
    rate_limit_storage_url: str = "memory://"
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
    # 超时与队列（PRD 5.4 / 5.6，12号 §3.3）
    # 旧同步端点（POST /questions/from-image）的单次调用上限。
    # 注意它是「每次 LLM 调用」而不是整单——识图两跳，整单最坏是两个它。
    recognize_client_timeout_s: int = 180
    # 识图任务化（B 档，05 §6.8）：提交拿单号 → 轮询取结果。
    # 典型等待 170s（准入估算 30 + 整单 140）；最坏 180s（准入只看估算，实际排队可到
    # 判死线 40 → 40 + 140）。前端轮询上限按最坏值 180s，不许按 170 收。
    # 排队时间确定、LLM 时间方差大，预算给后者：密页转录实测 90.2s + 结构化仍有余量。
    # 单次上限必须 ≤ 整单 −（结构化最坏 30 + 安全垫 5）= 105（见模块常量与 validator），
    # 再高就是赌第二跳跑不完。100 = 密页实测 90.2s + 约 11% 余量。
    vision_call_timeout_s: int = 100
    vision_run_deadline_s: int = 140
    # 准入闸：预估等待超它就在提交时 429（不先收单再判死）；
    # 判死闸 vision_queue_wait_max_s=40 留 10s 余量——估算有波动，放进来的人
    # 不能刚过线就被自己的排队超时判死。两个闸别合并成一个键。
    vision_admit_wait_max_s: int = 30
    vision_queue_wait_max_s: int = 40
    vision_max_concurrency: int = 8
    # 硬兜底，防"等待估算失准"时队列无限涨；正常参数下准入闸（30s）先触发。
    # 8 worker × 20s 下限 ⇒ 30s 时约 12 个排队，200 永远到不了，调了也没效果。
    vision_queue_max_depth: int = 50
    # force_refresh 的冷却：每次强刷都是一次 17–90s 的两跳调用，不设冷却等于成本放大器。
    # 只按"上一次强刷"计时——首次重新识别不受影响，挡的是连点/脚本刷
    vision_force_refresh_cooldown_s: int = 60
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

    # 录入草稿（05 §6.5b / 21号 §2.2）：PUT 的 content 序列化后字节上限（256 KB）
    draft_max_bytes: int = 256 * 1024

    # BYOK（ADR-007）：用户 AI Key 的加密密钥，Fernet key（32 字节 urlsafe base64）。
    # 留空 = /settings/ai 返回 503，不影响系统 Key 的既有链路。
    settings_encryption_key: str = ""

    @model_validator(mode="after")
    def _validate_vision_budget(self) -> Settings:
        """识图预算的不变量；放在 pydantic validator 里，任何进程 import 配置就校验，
        不依赖 FastAPI lifespan（单独起 worker 的进程也拦得住）。"""
        if self.vision_run_deadline_s > VISION_RUN_DEADLINE_MAX_S:
            raise ValueError(
                f"VISION_RUN_DEADLINE_S 不得超过 {VISION_RUN_DEADLINE_MAX_S}："
                "它和前端轮询上限 180s（实际排队 40 + 140）配套，单独调大会让前端提前放弃"
            )
        slack = STRUCTURE_WORST_CASE_S + SAFETY_MARGIN_S
        if self.vision_call_timeout_s > self.vision_run_deadline_s - slack:
            raise ValueError(
                "VISION_CALL_TIMEOUT_S 过大：第一跳会吃光整单预算"
                f"（必须 ≤ 整单 − {slack}，其中结构化最坏 {STRUCTURE_WORST_CASE_S}s"
                f" + 安全垫 {SAFETY_MARGIN_S}s，见 config 模块常量）"
            )
        return self

    def validate_for_startup(self) -> None:
        """启动时把密钥类配置一次性查完，而不是等第一个请求 500（13号 §4 / issue #11）。"""
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError(
                "JWT_SECRET 未配置或不足 32 字节（05 §9.4）；"
                "生成：python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if not self.llm_mock and not self.llm_api_key:
            raise RuntimeError("LLM_MOCK=false 但 LLM_API_KEY 未配置")
        if self.settings_encryption_key:
            # 非空就先构造一次：非法 key 不该等到第一个 BYOK 请求才炸
            try:
                from cryptography.fernet import Fernet

                Fernet(self.settings_encryption_key.encode())
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "SETTINGS_ENCRYPTION_KEY 不是合法的 Fernet key"
                ) from exc


settings = Settings()
