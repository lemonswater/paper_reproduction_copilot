from __future__ import annotations

import pytest

from app.job_runtime.errors import (
    JobConflictError,
)
from app.job_runtime.schemas import (
    JobInterrupt,
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


def _store_and_job(tmp_path):
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    record, _ = store.submit(
        job_id="job_api",
        idempotency_key="submit-api",
        thread_id="thread-api",
        run_id="run-api",
        run_dir=str(
            tmp_path / "runs" / "run-api"
        ),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(
            suffix="api"
        ),
        max_attempts=3,
        now=100.0,
    )
    return store, record


def _mark_waiting(store):
    worker = worker_fixture(
        worker_id="worker-test",
        session_id="session-test",
    )
    store.register_worker(
        worker=worker, lease_seconds=30
    )
    claim = store.claim_next(
        worker=worker,
        lease_seconds=30,
        now=101.0,
    )
    assert claim is not None
    return store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={},
            )
        ],
        result={},
        actor="worker-test",
        now=102.0,
    )


def test_resume_rejects_stale_version(
    tmp_path,
):
    store, _ = _store_and_job(
        tmp_path
    )
    waiting = _mark_waiting(store)

    with pytest.raises(
        JobConflictError,
        match="version",
    ):
        store.queue_resume(
            job_id=waiting.job_id,
            expected_node="human_review",
            value={
                "decision": "approved"
            },
            idempotency_key=(
                "resume-stale-version"
            ),
            actor="api",
            expected_job_version=(
                waiting.version - 1
            ),
            expected_wait_generation=(
                waiting.wait_generation
            ),
            now=103.0,
        )


def test_resume_idempotent_replay_wins_over_version(
    tmp_path,
):
    store, _ = _store_and_job(
        tmp_path
    )
    waiting = _mark_waiting(store)
    args = {
        "job_id": waiting.job_id,
        "expected_node": "human_review",
        "value": {
            "decision": "approved"
        },
        "idempotency_key": "resume-replay",
        "actor": "api",
        "expected_job_version": (
            waiting.version
        ),
        "expected_wait_generation": (
            waiting.wait_generation
        ),
        "now": 103.0,
    }

    first, first_created = (
        store.queue_resume(**args)
    )
    second, second_created = (
        store.queue_resume(**args)
    )

    assert first_created is True
    assert second_created is False
    assert (
        first.pending_resume_id
        == second.pending_resume_id
    )


def test_events_after_uses_strict_cursor(
    tmp_path,
):
    store, record = _store_and_job(
        tmp_path
    )
    first_page = store.list_events_after(
        record.job_id,
        after_event_id=0,
    )
    assert first_page

    cursor = first_page[-1].event_id
    assert store.list_events_after(
        record.job_id,
        after_event_id=cursor,
    ) == []


def test_cancel_is_idempotent(
    tmp_path,
):
    store, record = _store_and_job(
        tmp_path
    )

    first = store.request_cancel(
        job_id=record.job_id,
        reason="stop",
        actor="api",
        idempotency_key="cancel-1",
        expected_job_version=record.version,
        now=101.0,
    )
    second = store.request_cancel(
        job_id=record.job_id,
        reason="stop",
        actor="api",
        idempotency_key="cancel-1",
        # 重放时原 version 已经变化，但仍应返回旧命令结果。
        expected_job_version=record.version,
        now=102.0,
    )

    assert first.status == "cancelled"
    assert second.status == "cancelled"
    events = store.list_events(
        record.job_id
    )
    assert [
        item.event_type
        for item in events
    ].count("job_cancelled") == 1


def test_same_cancel_key_rejects_new_reason(
    tmp_path,
):
    store, record = _store_and_job(
        tmp_path
    )
    store.request_cancel(
        job_id=record.job_id,
        reason="first",
        actor="api",
        idempotency_key="cancel-conflict",
        expected_job_version=record.version,
        now=101.0,
    )

    with pytest.raises(
        JobConflictError,
        match="不同请求",
    ):
        store.request_cancel(
            job_id=record.job_id,
            reason="second",
            actor="api",
            idempotency_key=(
                "cancel-conflict"
            ),
            expected_job_version=(
                record.version
            ),
            now=102.0,
        )