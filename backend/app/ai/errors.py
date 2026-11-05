"""AI 模块的异常：调用层抛这些，service 层负责转成 ApiError + 写 ai_call_logs。

与 05 §6.2 的对应：AI_TIMEOUT / AI_PROVIDER_ERROR / AI_INVALID_OUTPUT。
"""
from __future__ import annotations


class AIError(Exception):
    """AI 模块异常基类；带 error_code 供上层映射。

    `message` 是子类兜底文案；给了 detail 就覆盖成实例属性——任务中心靠
    task.error_message 回答「为什么这道题生不出来」，只留兜底文案等于没日志。
    `raw_text` 是模型当时的原始输出，跟着异常交给上层写进 ai_call_logs。
    """

    error_code = "AI_PROVIDER_ERROR"
    message = "AI 服务错误"

    def __init__(self, detail: str | None = None, raw_text: str | None = None) -> None:
        super().__init__(detail or self.message)
        if detail:
            self.message = detail
        self.raw_text = raw_text


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
