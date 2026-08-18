from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.job_runtime.schemas import (
    JobInterrupt,
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.job_runtime.errors import (
    JobConflictError,
    LeaseLostError,
)
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


def _request() -> JobRequest:
    return JobRequest(
        paper_path="/data/paper.pdf",
        repo_path="/data/repo",
        experiment_goal="test",
        execution_profile_id="local",
    )


def _submit(
    store: SqliteJobStore,
    *,
    suffix: str = "1",
    now: float = 100.0,
):
    return store.submit(
        job_id=f"job_{suffix}",
        idempotency_key=f"submit_{suffix}",
        thread_id=f"thread_{suffix}",
        run_id=f"run_{suffix}",
        run_dir=f"/data/runs/run_{suffix}",
        request=_request(),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix=suffix),
        max_attempts=3,
        now=now,
    )


def test_submit_is_idempotent(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()

    first, first_created = _submit(store)
    second, second_created = _submit(store)

    assert first_created is True
    assert second_created is False
    assert first.job_id == second.job_id
    assert first.request_hash == second.request_hash


def test_same_idempotency_key_rejects_different_request(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    _submit(store)

    with pytest.raises(JobConflictError):
        store.submit(
            job_id="job_other",
            idempotency_key="submit_1",
            thread_id="thread_other",
            run_id="run_other",
            run_dir="/data/runs/run_other",
            request=JobRequest(
                paper_path="/data/other.pdf",
                repo_path="/data/repo",
                execution_profile_id="local",
            ),
            requirements=requirements_fixture(),
            initial_manifest=manifest_fixture(suffix="other"),
            max_attempts=3,
            now=100.0,
        )


def test_two_workers_only_one_can_claim(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    _submit(store)

    worker_a = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
    )
    worker_b = worker_fixture(
        worker_id="worker-b",
        session_id="session-b",
    )
    store.register_worker(
        worker=worker_a, lease_seconds=30
    )
    store.register_worker(
        worker=worker_b, lease_seconds=30
    )
    workers = {
        "worker-a": worker_a,
        "worker-b": worker_b,
    }

    def claim(worker_id: str):
        return store.claim_next(
            worker=workers[worker_id],
            lease_seconds=30,
            now=101.0,
        )

    with ThreadPoolExecutor(
        max_workers=2
    ) as pool:
        claims = list(
            pool.map(
                claim,
                ["worker-a", "worker-b"],
            )
        )

    claimed = [
        item for item in claims
        if item is not None
    ]
    assert len(claimed) == 1
    assert claimed[0].job.attempt_count == 1
    assert store.get("job_1").status == "running"


def test_heartbeat_requires_current_claim_token(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    _submit(store)
    worker = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
    )
    store.register_worker(
        worker=worker, lease_seconds=30
    )
    claim = store.claim_next(
        worker=worker,
        lease_seconds=10,
        now=101.0,
    )
    assert claim is not None

    heartbeat = store.heartbeat(
        job_id="job_1",
        claim_token=claim.claim_token,
        lease_seconds=10,
        now=105.0,
    )
    assert heartbeat.lease_renewed is True
    assert heartbeat.lease_expires_at.startswith(
        "1970-01-01T00:01:55"
    )

    with pytest.raises(LeaseLostError):
        store.heartbeat(
            job_id="job_1",
            claim_token="stale-token",
            lease_seconds=10,
            now=106.0,
        )


def test_expired_claim_can_be_requeued_and_old_token_is_fenced(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    _submit(store)
    worker_a = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
    )
    store.register_worker(
        worker=worker_a, lease_seconds=30
    )
    first = store.claim_next(
        worker=worker_a,
        lease_seconds=10,
        now=101.0,
    )
    assert first is not None

    expired = store.list_expired_running(
        now=112.0
    )
    assert [item.job_id for item in expired] == [
        "job_1"
    ]

    store.requeue_expired(
        job_id="job_1",
        expired_claim_token=first.claim_token,
        detail="no process records",
        actor="reconciler",
        now=112.0,
    )
    worker_b = worker_fixture(
        worker_id="worker-b",
        session_id="session-b",
    )
    store.register_worker(
        worker=worker_b, lease_seconds=30
    )
    second = store.claim_next(
        worker=worker_b,
        lease_seconds=10,
        now=113.0,
    )
    assert second is not None
    assert second.claim_token != first.claim_token

    with pytest.raises(LeaseLostError):
        store.mark_succeeded(
            job_id="job_1",
            claim_token=first.claim_token,
            result={"final_status": "succeeded"},
            actor="stale-worker",
            now=114.0,
        )

    current = store.get("job_1")
    assert current.worker_id == "worker-b"
    assert current.status == "running"


def test_waiting_resume_is_bound_to_node_and_generation(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    _submit(store)
    worker_a = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
    )
    store.register_worker(
        worker=worker_a, lease_seconds=30
    )
    first = store.claim_next(
        worker=worker_a,
        lease_seconds=10,
        now=101.0,
    )
    assert first is not None

    waiting = store.mark_waiting(
        job_id="job_1",
        claim_token=first.claim_token,
        interrupts=[
            JobInterrupt(
                node="command_selection",
                value_preview={"message": "choose"},
            )
        ],
        result={"run_id": "run_1"},
        actor="worker-a",
        now=102.0,
    )
    assert waiting.status == "waiting_for_input"
    assert waiting.wait_generation == 1

    with pytest.raises(JobConflictError):
        store.queue_resume(
            job_id="job_1",
            expected_node="human_review",
            value={"decision": "approved"},
            idempotency_key="resume-wrong",
            actor="cli",
            now=103.0,
        )

    resumed, created = store.queue_resume(
        job_id="job_1",
        expected_node="command_selection",
        value={
            "run_commands_hash": "abc",
            "selected_index": 0,
            "edits": [],
        },
        idempotency_key="resume-right",
        actor="cli",
        now=103.0,
    )
    assert created is True
    assert resumed.status == "queued"

    duplicate, duplicate_created = (
        store.queue_resume(
            job_id="job_1",
            expected_node="command_selection",
            value={
                "run_commands_hash": "abc",
                "selected_index": 0,
                "edits": [],
            },
            idempotency_key="resume-right",
            actor="cli",
            now=104.0,
        )
    )
    assert duplicate_created is False
    assert duplicate.job_id == "job_1"

    worker_b = worker_fixture(
        worker_id="worker-b",
        session_id="session-b",
    )
    store.register_worker(
        worker=worker_b, lease_seconds=30
    )
    second = store.claim_next(
        worker=worker_b,
        lease_seconds=10,
        now=105.0,
    )
    assert second is not None
    assert second.resume_request is not None
    assert (
        second.resume_request.expected_node
        == "command_selection"
    )
    assert second.resume_request.wait_generation == 1


def test_cancel_queued_is_terminal_but_running_is_cooperative(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    _submit(store, suffix="queued")
    queued = store.request_cancel(
        job_id="job_queued",
        reason="stop queued",
        actor="test",
        now=101.0,
    )
    assert queued.status == "cancelled"

    _submit(store, suffix="running")
    worker = worker_fixture(
        worker_id="worker",
        session_id="session-a",
    )
    store.register_worker(
        worker=worker, lease_seconds=30
    )
    claim = store.claim_next(
        worker=worker,
        lease_seconds=10,
        now=101.0,
    )
    assert claim is not None
    running = store.request_cancel(
        job_id=claim.job.job_id,
        reason="stop running",
        actor="test",
        now=102.0,
    )
    assert running.status == "cancelling"

    heartbeat = store.heartbeat(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        lease_seconds=10,
        now=103.0,
    )
    assert heartbeat.cancel_requested is True
    assert heartbeat.cancellation_reason == (
        "stop running"
    )