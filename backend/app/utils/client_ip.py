"""从请求里取「真实客户端 IP」。

`request.client.host` 在 nginx 反代后面恒等于代理地址，登录失败限流会把全站
用户算成同一个 IP（13号 §4.6）。所以只有当直连来源在 `TRUSTED_PROXIES` 里时
才读 `X-Forwarded-For`；否则任何客户端自己塞的头都不认。

`TRUSTED_PROXIES` 支持单个 IP 与 CIDR 网段：容器重建后网桥网关一般不变，
但写 `172.17.0.0/16` 这类网段比钉一个精确 IP 更稳——精确匹配一旦对不上，
限流会静默退化成"全站一个桶"，没有任何报错。
"""
from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache

from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# 拿不到来源时的占位；限流按这一个桶计，不会因为解析失败而放行
UNKNOWN = "unknown"


@lru_cache(maxsize=8)
def _networks(
    entries: tuple[str, ...],
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    parsed = []
    for entry in entries:
        try:
            parsed.append(ipaddress.ip_network(entry.strip(), strict=False))
        except ValueError:
            logger.warning("TRUSTED_PROXIES 里的 %r 不是合法 IP/网段，已忽略", entry)
    return tuple(parsed)


def _is_trusted(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in _networks(tuple(settings.trusted_proxies)))


def _rightmost_untrusted(hops: list[str]) -> str | None:
    """从右往左第一个不可信地址就是「离我最近的可信跳之外的客户端」。

    只取最左边一项是常见错误：那一项由客户端自己控制，可以伪造。
    """
    for hop in reversed(hops):
        address = hop.strip()
        if address and not _is_trusted(address):
            return address
    return None


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else None
    if peer is None:
        return UNKNOWN

    if not _is_trusted(peer):
        return peer

    header = request.headers.get("x-forwarded-for")
    if not header:
        return peer
    return _rightmost_untrusted(header.split(",")) or peer
