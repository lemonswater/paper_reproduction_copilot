from __future__ import annotations

from app.job_runtime.schemas import JobEvent
from app.notifications.projector import NotificationProjector
from app.notifications.repository import (
    SqliteNotificationRepository,
)


NOW = "2026-08-10T00:00:00+00:00"


class FakeJobEvents:
    def __init__(self, events: list[JobEvent]):
        self.events = events

    def events_global_after(
        self,
        *,
        after_event_id: int,
        limit: int,
    ) -> list[JobEvent]:
        return [
            event
            for event in self.events
            if event.event_id > after_event_id
        ][:limit]


def _event(
    event_id: int,
    event_type: str,
    payload: dict | None = None,
) -> JobEvent:
    return JobEvent(
        event_id=event_id,
        job_id="job-projector",
        event_type=event_type,
        actor="fixture",
        payload=payload or {},
        created_at=NOW,
    )


def _repository(tmp_path):
    repository = SqliteNotificationRepository(
        tmp_path / "notifications.sqlite"
    )
    repository.initialize()
    return repository


def test_waiting_and_resume_create_then_supersede(tmp_path) -> None:
    events = [
        _event(1, "job_submitted"),
        _event(
            2,
            "job_waiting_for_input",
            {
                "job_version": 4,
                "wait_generation": 2,
                "interrupt_nodes": ["human_review"],
            },
        ),
        _event(3, "job_resume_queued"),
    ]
    repository = _repository(tmp_path)
    projector = NotificationProjector(
        jobs=FakeJobEvents(events),
        repository=repository,
        batch_size=2,
    )

    assert projector.catch_up() == 3
    assert repository.projection_cursor() == 3
    records = repository.list_after()
    assert len(records) == 1
    assert records[0].kind == "approval_required"
    assert records[0].superseded_at is not None
    assert repository.unread_count() == 0

    # 第二次从持久 cursor 继续，不产生重复通知。
    assert projector.catch_up() == 0
    assert len(repository.list_after()) == 1


def test_worker_lost_then_claimed_creates_recovery(tmp_path) -> None:
    events = [
        _event(
            10,
            "job_lease_requeued",
            {
                "job_version": 3,
                "attempt_count": 1,
            },
        ),
        _event(
            11,
            "job_claimed",
            {
                "job_version": 4,
                "attempt_count": 2,
            },
        ),
    ]
    repository = _repository(tmp_path)
    projector = NotificationProjector(
        jobs=FakeJobEvents(events),
        repository=repository,
    )

    projector.catch_up()

    records = repository.list_after()
    assert [item.kind for item in records] == [
        "worker_lost",
        "job_recovered",
    ]
    assert records[0].superseded_at is not None
    assert records[1].superseded_at is None
    assert repository.unread_count() == 1


def test_normal_resume_claim_is_not_worker_recovery(tmp_path) -> None:
    events = [
        _event(
            20,
            "job_waiting_for_input",
            {
                "job_version": 2,
                "wait_generation": 1,
                "interrupt_nodes": ["human_review"],
            },
        ),
        _event(21, "job_resume_queued"),
        _event(
            22,
            "job_claimed",
            {
                "job_version": 4,
                "attempt_count": 2,
            },
        ),
    ]
    repository = _repository(tmp_path)
    NotificationProjector(
        jobs=FakeJobEvents(events),
        repository=repository,
    ).catch_up()

    assert all(
        item.kind != "job_recovered"
        for item in repository.list_after()
    )
