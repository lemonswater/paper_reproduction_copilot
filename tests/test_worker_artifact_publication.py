from __future__ import annotations

import pytest

from app.job_runtime.schemas import (
    JobExecutionOutcome,
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.job_runtime.worker import JobWorker
from app.storage.errors import (
    ArtifactBackendUnavailable,
)
from app.storage.schemas import (
    ArtifactPublicationReport,
)
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
    """避免单测依赖另一个 test module 的私有 helper。"""

    def __init__(self, outcome):
        self.outcome = outcome

    def execute(self, claim, heartbeat):
        del claim
        heartbeat.raise_if_unhealthy()
        return self.outcome


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
        run_dir=str(
            tmp_path / "runs/run-worker"
        ),
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


class RecordingPublisher:
    def __init__(self):
        self.calls = 0

    def publish(
        self,
        *,
        job,
        records,
        workspace_binding,
        ensure_active,
    ):
        self.calls += 1
        ensure_active()
        assert list(records) == []
        return ArtifactPublicationReport(
            artifact_count=0,
            published_count=0,
            reused_count=0,
            backend="local",
        )


class UnavailablePublisher:
    def publish(self, **kwargs):
        raise ArtifactBackendUnavailable(
            "controlled outage"
        )


def test_worker_publishes_before_succeeded(
    tmp_path,
    patched_worker_identity,
) -> None:
    store = _queued_store(tmp_path)
    publisher = RecordingPublisher()
    worker = JobWorker(
        worker_id="worker-storage",
        store=store,
        runner=OutcomeRunner(
            JobExecutionOutcome(
                status="succeeded",
                result={
                    "final_status": "succeeded"
                },
            )
        ),
        artifact_publisher=publisher,
        workspace_manager=PassThroughWorkspaceManager(
            binding_fixture(suffix="worker")
        ),
        lease_seconds=1.0,
        heartbeat_seconds=0.1,
    )

    worker.run_once()

    record = store.get("job-worker")
    assert publisher.calls == 1
    assert record.status == "succeeded"
    assert (
        record.result[
            "artifact_publication"
        ]["status"]
        == "completed"
    )


def test_temporary_storage_error_requeues(
    tmp_path,
    patched_worker_identity,
) -> None:
    store = _queued_store(tmp_path)
    worker = JobWorker(
        worker_id="worker-storage",
        store=store,
        runner=OutcomeRunner(
            JobExecutionOutcome(
                status="succeeded",
                result={},
            )
        ),
        artifact_publisher=(
            UnavailablePublisher()
        ),
        workspace_manager=PassThroughWorkspaceManager(
            binding_fixture(suffix="worker")
        ),
        lease_seconds=1.0,
        heartbeat_seconds=0.1,
    )

    worker.run_once()

    record = store.get("job-worker")
    assert record.status == "queued"
    assert (
        record.error["type"]
        == "ArtifactBackendUnavailable"
    )