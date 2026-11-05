"""从模型输出里提取 JSON。

模型偶尔会无视「只输出 JSON」的指令，包一层 ```json 代码块或在前后加说明文字，
所以这里做容错提取，而不是严格 json.loads 整段输出。
"""
from __future__ import annotations

import json

from app.ai.errors import AIInvalidOutputError

_FENCES = ("```json", "```")


def extract_json(text: str) -> dict | list:
    """按顺序尝试：整段解析 → 剥代码块 → 截第一个平衡的花括号/方括号块。"""
    candidates = [text.strip()]
    for fence in _FENCES:
        if fence in candidates[0]:
            candidates = [part.strip() for part in candidates[0].split(fence) if part.strip()]
            break

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    for candidate in candidates:
        block = _first_balanced_block(candidate)
        if block is not None:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                pass

    raise AIInvalidOutputError("无法从模型输出中提取 JSON")


def _first_balanced_block(text: str) -> str | None:
    """找到第一段括号配平的子串，处理『说明文字 {…} 说明文字』这种情况。"""
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
    return None
