from __future__ import annotations

import pytest

from app.notifications.errors import NotificationConflictError
from app.notifications.repository import (
    SqliteNotificationRepository,
)
from app.notifications.schemas import (
    NotificationDraft,
    NotificationProjection,
)


NOW = "2026-08-10T00:00:00+00:00"


def _repository(tmp_path) -> SqliteNotificationRepository:
    repository = SqliteNotificationRepository(
        tmp_path / "notifications.sqlite"
    )
    repository.initialize()
    return repository


def _projection(
    event_id: int,
    *,
    job_id: str = "job-notice",
    kind: str = "approval_required",
) -> NotificationProjection:
    draft = NotificationDraft(
        notification_id=f"notice-{event_id}",
        source_event_id=event_id,
        job_id=job_id,
        kind=kind,
        severity="warning",
        title="waiting",
        message="review current state",
        job_version=4,
        wait_generation=2,
        expected_node="human_review",
        operation_kind="submit_decision",
        created_at=NOW,
    )
    return NotificationProjection(
        source_event_id=event_id,
        job_id=job_id,
        event_type="job_waiting_for_input",
        event_created_at=NOW,
        notification=draft,
        supersede_operation_notifications=True,
    )


def test_projection_and_cursor_are_idempotent(tmp_path) -> None:
    repository = _repository(tmp_path)
    projection = _projection(10)

    assert repository.apply_projection(projection) is True
    assert repository.projection_cursor() == 10
    assert repository.apply_projection(projection) is False

    records = repository.list_after()
    assert len(records) == 1
    assert records[0].source_event_id == 10


def test_new_generation_supersedes_old_operation(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.apply_projection(_projection(10))
    repository.apply_projection(_projection(11))

    records = repository.list_after()
    assert len(records) == 2
    assert records[0].superseded_at is not None
    assert records[1].superseded_at is None
    assert repository.unread_count() == 1


def test_mark_read_uses_version_cas(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.apply_projection(_projection(10))

    record = repository.get("notice-10")
    updated = repository.mark_read(
        notification_id=record.notification_id,
        expected_version=record.version,
    )
    assert updated.read_at is not None
    assert repository.unread_count() == 0

    # 已读重复提交是幂等的，即使客户端仍带旧 version。
    replay = repository.mark_read(
        notification_id=record.notification_id,
        expected_version=record.version,
    )
    assert replay.read_at == updated.read_at


def test_supersede_makes_old_mark_read_version_stale(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.apply_projection(_projection(10))
    old = repository.get("notice-10")
    repository.apply_projection(_projection(11))

    with pytest.raises(
        NotificationConflictError,
        match="version",
    ):
        repository.mark_read(
            notification_id=old.notification_id,
            expected_version=old.version,
        )


def test_mark_all_does_not_touch_future_notifications(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.apply_projection(
        _projection(10, job_id="job-a")
    )
    first_seq = repository.list_after()[0].notification_seq
    repository.apply_projection(
        _projection(11, job_id="job-b")
    )

    assert repository.mark_all_read(
        through_sequence=first_seq
    ) == 1
    assert repository.unread_count() == 1
