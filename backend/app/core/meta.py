"""应用元数据默认值（PROJECT_NAME / VERSION / API_PREFIX）。

独立于 `config.Settings` 存在：`config.py` 在 import 时就实例化 `settings = Settings()`
（会读 `.env`）。导出 OpenAPI 的脚本要求「只按代码默认值导出、不受本机环境干扰」，
就必须在 import config 之前拿到这三个默认值——所以放在这里，由 config 与导出脚本共用，
避免同一组字面量出现两次。
"""
from __future__ import annotations

PROJECT_NAME = "Bababoi Learning Machine"
VERSION = "0.1.0"
API_PREFIX = "/api/v1"
