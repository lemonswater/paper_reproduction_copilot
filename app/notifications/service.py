from __future__ import annotations

from app.interaction.policy import allowed_operations
from app.job_runtime.errors import JobNotFoundError
from app.job_runtime.service import JobService
from app.notifications.ports import NotificationRepository
from app.notifications.projector import NotificationProjector
from app.notifications.schemas import (
    MarkNotificationsReadResponse,
    NotificationPage,
    NotificationRecord,
    NotificationUnreadCount,
    NotificationView,
)


class NotificationService:
    """通知用例层：先补投影，再公开安全视图。"""

    def __init__(
        self,
        *,
        jobs: JobService,
        repository: NotificationRepository,
        projector: NotificationProjector,
        max_sync_batches: int = 50,
    ):
        self.jobs = jobs
        self.repository = repository
        self.projector = projector
        self.max_sync_batches = max(1, max_sync_batches)

    def ping(self) -> None:
        self.repository.ping()

    def sync(self) -> int:
        return self.projector.catch_up(
            max_batches=self.max_sync_batches
        )

    def _current_operation(
        self,
        record: NotificationRecord,
    ):
        if record.operation_kind is None:
            return None, None
        if record.superseded_at is not None:
            return None, "通知对应的任务状态已经变化"
        if record.job_version is None:
            return None, "旧通知缺少 Job version，不能用于恢复"

        try:
            job = self.jobs.get(record.job_id)
        except JobNotFoundError:
            return None, "任务已经被清理"

        candidates = allowed_operations(job)
        for operation in candidates:
            if operation.kind != record.operation_kind:
                continue
            if (
                operation.expected_job_version
                != record.job_version
            ):
                continue
            if (
                operation.expected_wait_generation
                != record.wait_generation
            ):
                continue
            if operation.expected_node != record.expected_node:
                continue
            return operation, None

        return None, "当前任务不再提供该操作，请刷新任务详情"

    def _view(
        self,
        record: NotificationRecord,
    ) -> NotificationView:
        operation, stale_reason = self._current_operation(record)
        unread = (
            record.read_at is None
            and record.superseded_at is None
        )
        return NotificationView(
            notification_seq=record.notification_seq,
            notification_id=record.notification_id,
            version=record.version,
            source_event_id=record.source_event_id,
            job_id=record.job_id,
            kind=record.kind,
            severity=record.severity,
            title=record.title,
            message=record.message,
            unread=unread,
            superseded=(record.superseded_at is not None),
            created_at=record.created_at,
            updated_at=record.updated_at,
            current_operation=operation,
            stale_reason=stale_reason,
        )

    def list_notifications(
        self,
        *,
        after_sequence: int = 0,
        unread_only: bool = False,
        limit: int = 100,
    ) -> NotificationPage:
        self.sync()
        records = self.repository.list_after(
            after_sequence=after_sequence,
            unread_only=unread_only,
            limit=limit,
        )
        items = [self._view(record) for record in records]
        return NotificationPage(
            items=items,
            next_after=(
                items[-1].notification_seq
                if items
                else after_sequence
            ),
            unread_count=self.repository.unread_count(),
        )

    def unread_count(self) -> NotificationUnreadCount:
        self.sync()
        return NotificationUnreadCount(
            count=self.repository.unread_count()
        )

    def mark_read(
        self,
        *,
        notification_id: str,
        expected_version: int,
    ) -> NotificationView:
        # 先同步，避免把刚刚 supersede 的旧版本当成当前版本。
        self.sync()
        record = self.repository.mark_read(
            notification_id=notification_id,
            expected_version=expected_version,
        )
        return self._view(record)

    def mark_all_read(
        self,
        *,
        through_sequence: int,
    ) -> MarkNotificationsReadResponse:
        self.sync()
        updated = self.repository.mark_all_read(
            through_sequence=through_sequence
        )
        return MarkNotificationsReadResponse(
            updated_count=updated,
            through_sequence=through_sequence,
            unread_count=self.repository.unread_count(),
        )
