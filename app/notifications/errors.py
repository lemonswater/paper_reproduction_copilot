class NotificationError(RuntimeError):
    """通知领域错误基类。"""


class NotificationNotFoundError(NotificationError):
    """通知不存在或已被 Retention 清理。"""


class NotificationConflictError(NotificationError):
    """通知 version 已变化。"""
