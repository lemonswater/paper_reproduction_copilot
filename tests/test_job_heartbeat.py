from __future__ import annotations

import time

import pytest

from app.job_runtime.heartbeat import (
    JobCancellationRequested,
    LeaseHeartbeat,
)
from app.job_runtime.schemas import JobRequest
from app.job_runtime.store import SqliteJobStore
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


def _claimed_job(tmp_path):
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    now = time.time()
    store.submit(
        job_id="job-heartbeat",
        idempotency_key="submit-heartbeat",
        thread_id="thread-heartbeat",
        run_id="run-heartbeat",
        run_dir="/data/runs/run-heartbeat",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(
            suffix="heartbeat"
        ),
        max_attempts=3,
        now=now,
    )
    worker = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
    )
    store.register_worker(
        worker=worker, lease_seconds=30
    )
    claim = store.claim_next(
        worker=worker,
        lease_seconds=0.3,
        now=now,
    )
    assert claim is not None
    return store, claim


def test_heartbeat_thread_renews_lease(
    tmp_path,
) -> None:
    store, claim = _claimed_job(tmp_path)
    original = store.get(
        claim.job.job_id
    ).heartbeat_at

    heartbeat = LeaseHeartbeat(
        store=store,
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        lease_seconds=0.3,
        interval_seconds=0.05,
    )
    with heartbeat:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            current = store.get(
                claim.job.job_id
            ).heartbeat_at
            if current != original:
                break
            time.sleep(0.01)
        else:
            raise AssertionError(
                "heartbeat did not renew lease"
            )


def test_heartbeat_observes_cancel_request(
    tmp_path,
) -> None:
    store, claim = _claimed_job(tmp_path)
    heartbeat = LeaseHeartbeat(
        store=store,
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        lease_seconds=0.3,
        interval_seconds=0.05,
    )

    with heartbeat:
        store.request_cancel(
            job_id=claim.job.job_id,
            reason="test stop",
            actor="test",
        )
        deadline = time.monotonic() + 2
        while (
            not heartbeat.cancellation_requested
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)

        with pytest.raises(
            JobCancellationRequested
        ):
            heartbeat.raise_if_unhealthy()