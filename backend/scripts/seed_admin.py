"""管理端管理员种子脚本（ADM-002 / 28 号文档 §8）。

    cd backend
    ADMIN_USERNAME=admin ADMIN_PASSWORD='强口令' ADMIN_EMAIL=admin@example.com \
        uv run python scripts/seed_admin.py

    ADMIN_USERNAME=admin ADMIN_PASSWORD='新口令' uv run python scripts/seed_admin.py --reset --yes

规则：
- **没有默认账号、没有默认密码**：ADMIN_USERNAME / ADMIN_PASSWORD 缺失或为空直接退出。
- 管理员只能由本脚本（服务器 shell / 部署脚本）创建；公开注册永远只产生 student。
- `APP_ENV=production` 时拒绝运行；非 development/local 环境执行 `--reset` 必须加 `--yes`。
- 默认「只建不改」：账号已存在时只确保 role=admin，不碰密码（避免误把线上口令改掉）。
- `--reset` 才重写密码，并把 token_version +1（已登录的管理端立即失效）。
- 口令只从环境变量读，不打印、不写日志、不写审计。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

# Windows 控制台默认 GBK，中文汇总会打成乱码；与 seed_demo.py 同一个坑
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8")

import os  # noqa: E402

from pydantic import ValidationError  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import utcnow  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.schemas.auth import RegisterRequest  # noqa: E402


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def main(argv: list[str]) -> int:
    reset = "--reset" in argv
    yes = "--yes" in argv

    if settings.app_env == "production":
        print("seed_admin 禁止在生产环境运行（APP_ENV=production）", file=sys.stderr)
        return 2
    if reset and not yes and settings.app_env not in ("development", "local"):
        print("--reset 会覆盖现有管理员口令，非本地环境必须显式加 --yes", file=sys.stderr)
        return 2

    username = _env("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD", "")
    email = _env("ADMIN_EMAIL") or None

    if not username:
        print("缺少 ADMIN_USERNAME：管理员账号必须由环境变量指定", file=sys.stderr)
        return 2
    if not password:
        print(
            "缺少 ADMIN_PASSWORD：没有默认密码，口令只能由环境变量注入",
            file=sys.stderr,
        )
        return 2

    # 复用注册契约（用户名 3–32/字符集、bcrypt 72 字节）；脚本不能绕过校验造坏账号
    try:
        RegisterRequest(username=username, password=password, email=email)
    except ValidationError as exc:
        print(f"账号字段不合法：{exc.errors()[0]['msg']}", file=sys.stderr)
        return 2

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            session.add(
                User(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role="admin",
                    must_change_password=False,
                )
            )
            session.commit()
            print(f"已创建管理员：{username}")
            return 0

        changed: list[str] = []
        if user.role != "admin":
            user.role = "admin"
            changed.append("role=admin")
        if reset:
            user.password_hash = hash_password(password)
            # 口令变更要让已签发的管理端 token 全部失效（与学生改密同一语义）
            user.token_version += 1
            user.must_change_password = False
            user.temp_password_expires_at = None
            if email is not None:
                user.email = email
            changed.append("password")
            changed.append(f"token_version={user.token_version}")
        if not changed:
            session.rollback()
            print(
                f"管理员已存在，未修改：{username}（要重写口令加 --reset --yes）"
            )
            return 0

        user.updated_at = utcnow()
        session.commit()
        print(f"已更新管理员：{username}（{', '.join(changed)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
