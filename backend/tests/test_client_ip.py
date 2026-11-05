"""真实客户端 IP 的取法（issue #11 BE-003：nginx 后面 request.client.host 是代理地址）。

规则：只有直连来源在 `TRUSTED_PROXIES` 里时才读 `X-Forwarded-For`，
并且从右往左取第一个不可信地址——最左那项是客户端自己写的，想填什么填什么。
"""
from __future__ import annotations

import pytest
from fastapi import Request

from app.core.config import settings
from app.utils.client_ip import client_ip


def _request(peer: str | None, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (peer, 1234) if peer else None,
    }
    return Request(scope)


@pytest.fixture()
def trusted(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxies", ["10.0.0.2"])


def test_direct_connection_ignores_forwarded_header() -> None:
    """没配可信代理时，客户端自己塞的 X-Forwarded-For 一律不认。"""
    req = _request("203.0.113.9", {"X-Forwarded-For": "8.8.8.8"})
    assert client_ip(req) == "203.0.113.9"


def test_single_hop_proxy_uses_forwarded_value(trusted) -> None:
    req = _request("10.0.0.2", {"X-Forwarded-For": "203.0.113.9"})
    assert client_ip(req) == "203.0.113.9"


def test_spoofed_left_entry_is_not_trusted(trusted) -> None:
    """`伪造IP, 真实IP` 这种链：取右边那个不可信的，不取最左。"""
    req = _request("10.0.0.2", {"X-Forwarded-For": "1.1.1.1, 203.0.113.9"})
    assert client_ip(req) == "203.0.113.9"


def test_proxy_without_forwarded_header_falls_back_to_peer(trusted) -> None:
    req = _request("10.0.0.2")
    assert client_ip(req) == "10.0.0.2"


def test_missing_peer_is_reported_as_unknown() -> None:
    assert client_ip(_request(None)) == "unknown"
