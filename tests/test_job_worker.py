from __future__ import annotations

import pytest

from app.job_runtime.schemas import (
    JobExecutionOutcome,
    JobInterrupt,
    JobRequest,
)
from app.job_runtime.store import SqliteJobStore
from app.job_runtime.worker import JobWorker
from tests.workspace_helpers import (
    PassThroughWorkspaceManager,
    binding_fixture,
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


@pytest.fixture
def patched_worker_identity(monkeypatch):
    """JobWorker.run_once() 启动 session heartbeat 时会调用
    build_worker_identity → load_worker_capabilities 读取真实磁盘文件。

    单测使用 fake worker，直接替换为固定 WorkerIdentity，避免依赖
    worker_capabilities_path 与执行 profile 配置。
    """

    def fake_build_worker_identity(
        *,
        worker_id,
        worker_session_id=None,
    ):
        return worker_fixture(
            worker_id=worker_id,
            session_id=(
                worker_session_id or "session-a"
            ),
        )

    monkeypatch.setattr(
        "app.job_runtime.worker.build_worker_identity",
        fake_build_worker_identity,
    )


class OutcomeRunner:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def execute(self, claim, heartbeat):
        self.calls += 1
        heartbeat.raise_if_unhealthy()
        return self.outcome


class FailingRunner:
    def execute(self, claim, heartbeat):
        raise RuntimeError(
            "controlled runner failure"
        )


def _queued_store(tmp_path):
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    store.submit(
        job_id="job-worker",
        idempotency_key="submit-worker",
        thread_id="thread-worker",
        run_id="run-worker",
        run_dir=str(tmp_path / "runs/run-worker"),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="worker"),
        max_attempts=3,
    )
    return store


def _worker(store, runner):
    return JobWorker(
        worker_id="worker-test",
        store=store,
        runner=runner,
        workspace_manager=PassThroughWorkspaceManager(
            binding_fixture(suffix="worker")
        ),
        lease_seconds=1.0,
        heartbeat_seconds=0.1,
        poll_seconds=0.01,
    )


def test_worker_marks_graph_terminal_as_job_succeeded(
    tmp_path,
    patched_worker_identity,
) -> None:
    store = _queued_store(tmp_path)
    runner = OutcomeRunner(
        JobExecutionOutcome(
            status="succeeded",
            result={
                "final_status": "preflight_failed",
                "run_id": "run-worker",
            },
        )
    )

    handled = _worker(
        store,
        runner,
    ).run_once()

    assert handled is True
    assert runner.calls == 1
    record = store.get("job-worker")
    assert record.status == "succeeded"
    # Job 成功与业务 final_status 分层。
    assert (
        record.result["final_status"]
        == "preflight_failed"
    )


def test_worker_persists_interrupt_as_waiting(
    tmp_path,
    patched_worker_identity,
) -> None:
    store = _queued_store(tmp_path)
    runner = OutcomeRunner(
        JobExecutionOutcome(
            status="waiting_for_input",
            result={"run_id": "run-worker"},
            interrupts=[
                JobInterrupt(
                    node="patch_review",
                    value_preview={
                        "patch_sha256": "abc"
                    },
                )
            ],
        )
    )

    _worker(store, runner).run_once()

    record = store.get("job-worker")
    assert (
        record.status
        == "waiting_for_input"
    )
    assert record.interrupt_nodes == [
        "patch_review"
    ]
    assert record.wait_generation == 1


def test_worker_records_unhandled_runner_error(
    tmp_path,
    patched_worker_identity,
) -> None:
    store = _queued_store(tmp_path)

    _worker(
        store,
        FailingRunner(),
    ).run_once()

    record = store.get("job-worker")
    assert record.status == "failed"
    assert record.error["type"] == (
        "RuntimeError"
    )
    assert "controlled runner failure" in (
        record.error["message"]
    )