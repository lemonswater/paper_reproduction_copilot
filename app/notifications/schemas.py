from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.interaction.schemas import AllowedOperation


NotificationKind = Literal[
    "approval_required",
    "input_required",
    "job_failed",
    "job_succeeded",
    "worker_lost",
    "job_recovered",
]

NotificationSeverity = Literal[
    "info",
    "success",
    "warning",
    "error",
]

NotificationOperationKind = Literal[
    "submit_decision",
    "operator_reconciliation_required",
]


class NotificationModel(BaseModel):
    """通知协议拒绝未知字段，防止操作身份静默扩张。"""

    model_config = ConfigDict(extra="forbid")


class NotificationDraft(NotificationModel):
    """Projector 根据一个 JobEvent 产生的安全投影草稿。"""

    notification_id: str = Field(min_length=1, max_length=100)
    source_event_id: int = Field(ge=1)
    job_id: str = Field(min_length=1, max_length=200)
    kind: NotificationKind
    severity: NotificationSeverity
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1000)

    # 这些是事件发生时的身份快照，不是永久有效的操作授权。
    job_version: int | None = Field(default=None, ge=0)
    wait_generation: int | None = Field(default=None, ge=1)
    expected_node: str | None = Field(
        default=None,
        max_length=100,
    )
    operation_kind: NotificationOperationKind | None = None
    created_at: str


class NotificationRecord(NotificationDraft):
    """Notification Repository 的完整持久化对象。"""

    notification_seq: int = Field(ge=1)
    version: int = Field(ge=0)
    read_at: str | None = None
    superseded_at: str | None = None
    updated_at: str


class NotificationProjection(NotificationModel):
    """一个 JobEvent 对通知 Materialized View 的确定性变更。"""

    source_event_id: int = Field(ge=1)
    job_id: str
    event_type: str
    event_created_at: str
    notification: NotificationDraft | None = None

    # 新等待代次、resume 或终态会让旧操作通知不再 actionable。
    supersede_operation_notifications: bool = False
    # recovery/terminal 可以关闭旧 worker_lost 提醒。
    supersede_worker_lost: bool = False


class NotificationView(NotificationModel):
    """公开 API 视图，不包含原始 JobEvent payload。"""

    notification_seq: int
    notification_id: str
    version: int
    source_event_id: int
    job_id: str
    kind: NotificationKind
    severity: NotificationSeverity
    title: str
    message: str
    unread: bool
    superseded: bool
    created_at: str
    updated_at: str

    # 只有与最新 JobView 精确匹配时才非空。
    current_operation: AllowedOperation | None = None
    stale_reason: str | None = None


class NotificationPage(NotificationModel):
    items: list[NotificationView] = Field(default_factory=list)
    next_after: int = Field(ge=0)
    unread_count: int = Field(ge=0)


class NotificationUnreadCount(NotificationModel):
    count: int = Field(ge=0)


class MarkNotificationReadRequest(NotificationModel):
    expected_notification_version: int = Field(ge=0)


class MarkNotificationsReadRequest(NotificationModel):
    """只把客户端已经观察到的游标范围标为已读。"""

    through_sequence: int = Field(ge=0)


class MarkNotificationsReadResponse(NotificationModel):
    updated_count: int = Field(ge=0)
    through_sequence: int = Field(ge=0)
    unread_count: int = Field(ge=0)
