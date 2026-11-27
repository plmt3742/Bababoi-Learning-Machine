"""审计动作码与中文名的映射（ADM-008）。

列表搜索要同时命中中文动作名和原始 action code：管理员在搜索框里输入「通过密码
申请」应该能查到 `password_request.approve`。映射集中在这里，写操作与列表共用。
"""
from __future__ import annotations

ACTION_LABELS: dict[str, str] = {
    "admin.login": "管理员登录",
    "admin.logout": "管理员退出",
    "user.disable": "禁用用户",
    "user.enable": "启用用户",
    "user.force_logout": "强制下线",
    "password_request.approve": "通过密码申请",
    "password_request.reject": "拒绝密码申请",
    "password_request.regenerate": "重新生成临时密码",
    "question.hide": "隐藏错题",
    "question.restore": "恢复错题",
    "question.flag": "标记异常",
    "question.unflag": "取消标记",
    "task.retry": "重试任务",
    "task.cancel": "取消任务",
    "ai_log.view_raw": "查看 AI 原始输出",
    "audit.export": "导出审计",
    "alert.ack": "确认告警",
    "alert.unack": "取消告警确认",
}


def label(action: str) -> str:
    return ACTION_LABELS.get(action, action)


def actions_matching(keyword: str) -> list[str]:
    """中文关键字能命中的 action 码；英文关键字直接按原样搜 code。"""
    needle = keyword.strip().lower()
    return [
        action
        for action, name in ACTION_LABELS.items()
        if needle and needle in name.lower()
    ]
