from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.notifications.schemas import (
    NotificationProjection,
    NotificationRecord,
)


@runtime_checkable
class NotificationRepository(Protocol):
    def initialize(self) -> None:
        ...

    def ping(self) -> None:
        ...

    def close(self) -> None:
        ...

    def projection_cursor(self) -> int:
        ...

    def apply_projection(
        self,
        projection: NotificationProjection,
    ) -> bool:
        """原子应用投影并推进 cursor；返回是否首次处理。"""
        ...

    def get(
        self,
        notification_id: str,
    ) -> NotificationRecord:
        ...

    def list_after(
        self,
        *,
        after_sequence: int = 0,
        unread_only: bool = False,
        limit: int = 100,
    ) -> list[NotificationRecord]:
        ...

    def unread_count(self) -> int:
        ...

    def has_active_kind(
        self,
        *,
        job_id: str,
        kind: str,
    ) -> bool:
        ...

    def mark_read(
        self,
        *,
        notification_id: str,
        expected_version: int,
    ) -> NotificationRecord:
        ...

    def mark_all_read(
        self,
        *,
        through_sequence: int,
    ) -> int:
        ...

    def delete_for_job(self, job_id: str) -> int:
        ...
