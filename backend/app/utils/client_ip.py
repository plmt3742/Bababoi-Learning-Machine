"""从请求里取「真实客户端 IP」。

`request.client.host` 在 nginx 反代后面恒等于代理地址，登录失败限流会把全站
用户算成同一个 IP（13号 §4.6）。所以只有当直连来源在 `TRUSTED_PROXIES` 里时
才读 `X-Forwarded-For`；否则任何客户端自己塞的头都不认。
"""
from __future__ import annotations

from fastapi import Request

from app.core.config import settings

# 拿不到来源时的占位；限流按这一个桶计，不会因为解析失败而放行
UNKNOWN = "unknown"


def _rightmost_untrusted(hops: list[str], trusted: list[str]) -> str | None:
    """从右往左第一个不在可信列表里的地址就是「离我最近的可信跳之外的客户端」。

    只取最左边一项是常见错误：那一项由客户端自己控制，可以伪造。
    """
    for hop in reversed(hops):
        address = hop.strip()
        if address and address not in trusted:
            return address
    return None


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else None
    if peer is None:
        return UNKNOWN

    if peer not in settings.trusted_proxies:
        return peer

    header = request.headers.get("x-forwarded-for")
    if not header:
        return peer
    return _rightmost_untrusted(header.split(","), settings.trusted_proxies) or peer
