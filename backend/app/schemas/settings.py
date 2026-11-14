"""个人设置（05 §6.9）。本期只有生成偏好一项，BYOK 的 `/settings/ai` 在 BE-020 里补。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, StrictBool

AiProvider = Literal["deepseek", "openai_compatible"]


class PreferencesOut(BaseModel):
    """`GET/PUT /settings/preferences` 的返回。

    `updated_at` 是这一行的最后写入时间，前端"保存成功"提示直接读它，
    不用比对自己发请求的时刻（跨设备时浏览器时钟不可信，同草稿那条理由）。
    """

    enforce_same_question_type: bool
    updated_at: datetime


class PreferencesUpdate(BaseModel):
    """`PUT /settings/preferences` 的请求体。

    缺字段按默认值 `true` 处理——默认开启是产品决策（issue #44），
    所以"没提交"和"提交了 true"必须是同一个结果，不能一个是开一个是未知。

    用 StrictBool 而不是 bool：pydantic 默认会把 `"yes"`/`"1"`/`"no"` 悄悄转成布尔，
    这是一个会改变生成失败率的开关，宁可让前端拿到 422 也别猜错它的意图。
    """

    enforce_same_question_type: StrictBool = True


class AiSettingsOut(BaseModel):
    """`GET/PUT /settings/ai` 的返回；任何情况下都不含原始 Key。"""

    configured: bool
    provider: AiProvider | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_masked: str | None = None
    updated_at: datetime | None = None


class AiSettingsUpdate(BaseModel):
    """`PUT /settings/ai` 的请求体。

    `api_key` 最少 8 位与前端设置页一致；`base_url` 只有 openai_compatible 必填，
    且必须 https + 白名单 host（SSRF 面先收窄）。
    """

    provider: AiProvider
    base_url: str | None = Field(default=None, max_length=255)
    model: str = Field(min_length=1, max_length=64)
    api_key: str = Field(min_length=8, max_length=512)
