"""LIKE 搜索的转义工具（复核单 P3）。

`q=%` 或 `q=_` 不转义时会被当通配符，管理员搜一个下划线会命中近乎全表。
调用方需传 `escape="\\\\"`，SQLite 与 MySQL 才会把反斜杠当转义符。
"""
from __future__ import annotations

import re

_LIKE_SPECIAL = re.compile(r"([%_\\])")


def contains_pattern(keyword: str) -> str:
    r"""把用户输入包成 `%...%`，并转义 `%`、`_`、`\`。"""
    return "%" + _LIKE_SPECIAL.sub(r"\\\1", keyword) + "%"
