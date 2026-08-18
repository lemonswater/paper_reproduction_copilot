from __future__ import annotations

from datetime import datetime, timezone

from app.job_runtime.schemas import (
    JobEvent,
    JobInterrupt,
    JobRecord,
    JobRequest,
)
from app.notifications.projector import NotificationProjector
from app.notifications.repository import (
    SqliteNotificationRepository,
)
from app.notifications.service import NotificationService
from tests.workspace_helpers import requirements_fixture


NOW = datetime.now(timezone.utc).isoformat()


def _waiting_job(
    *,
    version: int = 4,
    generation: int = 2,
) -> JobRecord:
    return JobRecord(
        job_id="job-notification-service",
        idempotency_key="submit-notification-service",
        request_hash="request-hash",
        thread_id="thread-notification-service",
        run_id="run-notification-service",
        run_dir="/data/runs/run-notification-service",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        workspace_manifest_id="manifest-notification-service",
        workspace_manifest_generation=1,
        workspace_assignment_epoch=1,
        status="waiting_for_input",
        version=version,
        attempt_count=1,
        max_attempts=3,
        wait_generation=generation,
        available_at=NOW,
        interrupt_nodes=["human_review"],
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={"message": "review"},
            )
        ],
        created_at=NOW,
        updated_at=NOW,
    )


class FakeJobs:
    def __init__(self):
        self.current = _waiting_job()
        self.events = [
            JobEvent(
                event_id=1,
                job_id=self.current.job_id,
                event_type="job_waiting_for_input",
                actor="worker",
                payload={
                    "job_version": 4,
                    "wait_generation": 2,
                    "interrupt_nodes": ["human_review"],
                },
                created_at=NOW,
            )
        ]

    def get(self, job_id: str) -> JobRecord:
        assert job_id == self.current.job_id
        return self.current

    def events_global_after(
        self,
        *,
        after_event_id: int,
        limit: int,
    ):
        return [
            item
            for item in self.events
            if item.event_id > after_event_id
        ][:limit]


def _service(tmp_path):
    jobs = FakeJobs()
    repository = SqliteNotificationRepository(
        tmp_path / "notifications.sqlite"
    )
    repository.initialize()
    projector = NotificationProjector(
        jobs=jobs,
        repository=repository,
    )
    return (
        NotificationService(
            jobs=jobs,
            repository=repository,
            projector=projector,
        ),
        jobs,
    )


def test_matching_wait_identity_returns_current_operation(
    tmp_path,
) -> None:
    service, _jobs = _service(tmp_path)

    item = service.list_notifications().items[0]

    assert item.current_operation is not None
    assert item.current_operation.kind == "submit_decision"
    assert item.current_operation.expected_job_version == 4
    assert item.current_operation.expected_wait_generation == 2
    assert item.current_operation.expected_node == "human_review"


def test_stale_job_generation_removes_operation(tmp_path) -> None:
    service, jobs = _service(tmp_path)
    first = service.list_notifications().items[0]
    assert first.current_operation is not None

    jobs.current = _waiting_job(version=6, generation=3)
    stale = service.list_notifications().items[0]

    assert stale.current_operation is None
    assert stale.stale_reason


def test_mark_read_updates_public_unread(tmp_path) -> None:
    service, _jobs = _service(tmp_path)
    item = service.list_notifications().items[0]

    updated = service.mark_read(
        notification_id=item.notification_id,
        expected_version=item.version,
    )

    assert updated.unread is False
    assert service.unread_count().count == 0
