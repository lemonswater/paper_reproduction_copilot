from __future__ import annotations

import os

import psutil

from app.config import settings
from app.execution.cancellation import (
    write_runtime_record,
)
from app.job_runtime.process_reconcile import (
    JobReconciler,
)
from app.job_runtime.schemas import JobRequest
from app.job_runtime.store import SqliteJobStore
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


def _expired_job(
    tmp_path,
    monkeypatch,
    *,
    suffix: str,
):
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / f"run-{suffix}"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    store = SqliteJobStore(
        tmp_path / f"{suffix}.sqlite"
    )
    store.initialize()
    store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=str(run_dir),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix=suffix),
        max_attempts=3,
        now=100.0,
    )
    worker = worker_fixture(
        worker_id="dead-worker",
        session_id="session-dead",
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
    return store, claim, run_dir


def test_expired_job_without_process_record_is_requeued(
    tmp_path,
    monkeypatch,
) -> None:
    store, claim, _ = _expired_job(
        tmp_path,
        monkeypatch,
        suffix="none",
    )
    changed = JobReconciler(
        store=store,
        actor="reconciler",
    ).reconcile_expired(now=112.0)

    assert changed == 1
    record = store.get(claim.job.job_id)
    assert record.status == "queued"
    assert record.claim_token is None


def test_finished_process_record_requires_reconciliation(
    tmp_path,
    monkeypatch,
) -> None:
    store, claim, run_dir = _expired_job(
        tmp_path,
        monkeypatch,
        suffix="finished",
    )
    write_runtime_record(
        run_dir=run_dir,
        execution_id="exec-finished",
        payload={
            "execution_id": "exec-finished",
            "status": "finished",
            "started_at": claim.job.claimed_at,
            "finished_at": (
                "1970-01-01T00:01:50+00:00"
            ),
            "returncode": 0,
        },
    )

    JobReconciler(
        store=store,
        actor="reconciler",
    ).reconcile_expired(now=112.0)

    record = store.get(claim.job.job_id)
    assert (
        record.status
        == "reconciliation_required"
    )
    assert (
        record.reconciliation["disposition"]
        == "finished_process_without_checkpoint"
    )


def test_live_exact_process_is_never_auto_requeued(
    tmp_path,
    monkeypatch,
) -> None:
    store, claim, run_dir = _expired_job(
        tmp_path,
        monkeypatch,
        suffix="active",
    )
    pid = os.getpid()
    write_runtime_record(
        run_dir=run_dir,
        execution_id="exec-active",
        payload={
            "execution_id": "exec-active",
            "status": "running",
            "started_at": claim.job.claimed_at,
            "pid": pid,
            "pgid": os.getpgid(pid),
            "process_create_time": (
                psutil.Process(pid).create_time()
            ),
        },
    )

    JobReconciler(
        store=store,
        actor="reconciler",
    ).reconcile_expired(now=112.0)

    record = store.get(claim.job.job_id)
    assert (
        record.status
        == "reconciliation_required"
    )
    assert (
        record.reconciliation["disposition"]
        == "active_process"
    )