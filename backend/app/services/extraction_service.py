"""识图提取（BE-014 / 05 §7.0）：把已上传的图转成 1..N 条可编辑题目条目。

链路上的三个决定，都是实测逼出来的，不是风格问题：

1. **同步跑，超时不自动重试**（14 号 §5-4）。一次识图实测开 `response_format=json_object`
   是 7.7s，不开会跑偏到 44.1s / 7265 token；再叠一层重试等于把用户的等待时间翻倍，
   而识图失败用户本来就能立刻"重传/改文本"。
2. **只有坏输出重试 1 次**（05 §7.0）。解析不出来、整个 JSON 形状不对，重抛一次是划算的；
   这一层由 pipeline 的 `retry_limit=1` 承担。
3. **校验失败对外报 `AI_INVALID_IMAGE`，不是 `AI_INVALID_OUTPUT`**。对用户来说这两件事
   是同一句"这张图没认出来"，而后者的措辞会把排查方向带偏到 prompt 上。
"""
from __future__ import annotations

import threading

from sqlalchemy.orm import sessionmaker

from app.ai import prompts, validator
from app.ai.client import OPERATION_VISION, build_llm_client
from app.ai.errors import AIError, AIInvalidImageError, AIInvalidOutputError, AITruncatedError
from app.ai.pipeline import run as pipeline_run
from app.services import ai_log, image_service

_client = None
_client_lock = threading.Lock()


def _llm_client():
    """识图用的客户端；测试 monkeypatch 这个函数换替身（和 task_worker 同一套路）。

    这里挂的是连接池，每个请求新建一个就等于每张图重新 TLS 握手，所以按进程缓存一份。
    """
    global _client
    with _client_lock:
        if _client is None:
            _client = build_llm_client()
        return _client


def extract_from_image(
    session_factory: sessionmaker,
    user_id: int,
    image_path: str,
    subject: str | None = None,
) -> dict:
    """返回 `{"image_path", "questions": [ExtractedQuestion], "warnings": [str]}`。

    图片不属于当前用户或文件已不在 → `image_service` 直接 404，不告诉调用方"存在但没权限"。
    """
    data_url = image_service.data_url_for_llm(user_id, image_path)
    messages = prompts.vision_messages(data_url, subject)
    try:
        result = pipeline_run(
            _llm_client(), OPERATION_VISION, messages,
            custom_validate=validator.validate_extraction,
            retry_limit=1,
        )
    except AITruncatedError as exc:
        # 实测一张真实教材照片 4 道题就吃掉 6776 输出 token（上限 8000），
        # 一页更密的题确实会顶到。这时候用户能做的只有把图裁小一点，
        # 所以文案要给动作，不给 "AI_INVALID_OUTPUT"。
        message = "这张图题目太多，识别结果被截断了；请裁剪成几次再上传"
        ai_log.write_call_log(session_factory, user_id, OPERATION_VISION, status="error",
                              error_code="AI_INVALID_IMAGE", raw_text=exc.raw_text)
        raise AIInvalidImageError(message, raw_text=exc.raw_text) from None
    except AIInvalidOutputError as exc:
        ai_log.write_call_log(session_factory, user_id, OPERATION_VISION, status="error",
                              error_code="AI_INVALID_IMAGE", raw_text=exc.raw_text)
        raise AIInvalidImageError(exc.message, raw_text=exc.raw_text) from None
    except AIError as exc:
        # 超时/供应商错误也要留一条：没有这行，识图失败在成本与延迟统计里就是隐身的
        ai_log.write_call_log(session_factory, user_id, OPERATION_VISION, status="error",
                              error_code=exc.error_code, raw_text=exc.raw_text)
        raise

    value = result.value
    ai_log.write_call_log(session_factory, user_id, OPERATION_VISION, status="success",
                          usage=result.usage, raw_text=result.usage.text)
    return {
        "image_path": image_path,
        # 出 model_dump 而不是 validator 的模型对象：响应模型是 schemas.image 那一套，
        # 跨模块的 pydantic 实例不会自动互认，直接把服务返回值变成可序列化的 dict 更干净
        "questions": [item.model_dump() for item in value["questions"]],
        "warnings": value["warnings"],
    }
