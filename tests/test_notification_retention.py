from __future__ import annotations

from app.notifications.repository import (
    SqliteNotificationRepository,
)
from app.notifications.schemas import (
    NotificationDraft,
    NotificationProjection,
)


NOW = "2026-08-10T00:00:00+00:00"


def _draft(event_id: int, job_id: str = "job-retention"):
    return NotificationDraft(
        notification_id=f"notice-{event_id}",
        source_event_id=event_id,
        job_id=job_id,
        kind="approval_required",
        severity="warning",
        title="test",
        message="retention test",
        job_version=1,
        wait_generation=1,
        expected_node="human_review",
        operation_kind="submit_decision",
        created_at=NOW,
    )


def _projection(event_id: int, job_id: str = "job-retention"):
    return NotificationProjection(
        source_event_id=event_id,
        job_id=job_id,
        event_type="job_waiting_for_input",
        event_created_at=NOW,
        notification=_draft(event_id, job_id),
        supersede_operation_notifications=True,
    )


def test_delete_for_job_is_idempotent(tmp_path) -> None:
    repository = SqliteNotificationRepository(
        tmp_path / "notifications.sqlite"
    )
    repository.initialize()

    repository.apply_projection(_projection(1, job_id="job-a"))
    repository.apply_projection(_projection(2, job_id="job-b"))

    assert repository.unread_count() == 2

    deleted = repository.delete_for_job("job-a")
    assert deleted == 1
    assert repository.unread_count() == 1

    # 二次删除是幂等的。
    deleted_again = repository.delete_for_job("job-a")
    assert deleted_again == 0
    assert repository.unread_count() == 1
