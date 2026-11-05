"""AI 模块的异常：调用层抛这些，service 层负责转成 ApiError + 写 ai_call_logs。

与 05 §6.2 的对应：AI_TIMEOUT / AI_PROVIDER_ERROR / AI_INVALID_OUTPUT。
"""
from __future__ import annotations


class AIError(Exception):
    """AI 模块异常基类；带 error_code 供上层映射。"""

    error_code = "AI_PROVIDER_ERROR"
    message = "AI 服务错误"


class AITimeoutError(AIError):
    error_code = "AI_TIMEOUT"
    message = "AI 服务超时"


class AIProviderError(AIError):
    error_code = "AI_PROVIDER_ERROR"
    message = "LLM 供应商错误"


class AIInvalidOutputError(AIError):
    """模型输出解析/校验失败——重试后仍失败才抛这个。"""

    error_code = "AI_INVALID_OUTPUT"
    message = "AI 输出无法解析或未通过校验"


class AIInvalidImageError(AIError):
    error_code = "AI_INVALID_IMAGE"
    message = "图片无法识别为题目"
