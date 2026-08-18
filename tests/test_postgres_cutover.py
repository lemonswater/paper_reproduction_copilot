from __future__ import annotations

"""PostgreSQL cutover smoke tests.

验证 factory 在 ``JOB_STORE_BACKEND=postgresql`` 时正确组装
``PostgresJobStore`` 和 ``PostgresArtifactRepository``，并能在切换后完成
一次完整的 submit -> claim -> succeed 端到端流转。

这些测试不调用 Graph、不连接 Provider，只验证控制面 wiring。
"""

import os

import pytest

from app.config import settings
from app.job_runtime.postgres_store import (
    PostgresJobStore,
)
from app.persistence.database import close_engine
from app.storage.postgres_artifact_repository import (
    PostgresArtifactRepository,
)


pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_backend(
    postgres_engine,
    monkeypatch,
):
    """把 settings 切到 postgresql backend，并清理全局 engine 缓存。"""

    monkeypatch.setattr(
        settings,
        "job_store_backend",
        "postgresql",
    )
    monkeypatch.setattr(
        settings,
        "database_url",
        os.environ["TEST_DATABASE_URL"],
    )
    # 清理可能由其他测试缓存的全局 engine，确保 build_engine 读到新 URL。
    close_engine()
    yield
    close_engine()


def test_build_job_store_returns_postgres(
    postgres_backend,
) -> None:
    from app.job_runtime.factory import build_job_store

    store = build_job_store()
    assert isinstance(store, PostgresJobStore)
    store.ping()
    store.close()


def test_build_artifact_storage_uses_postgres(
    postgres_backend,
) -> None:
    from app.storage.factory import build_artifact_storage

    bundle = build_artifact_storage()
    assert isinstance(
        bundle.repository,
        PostgresArtifactRepository,
    )
    bundle.repository.initialize()


def test_full_submit_claim_succeed_cutover(
    postgres_backend,
) -> None:
    """切换后端后，完整 submit -> claim -> mark_succeeded 流转正常。"""

    from app.job_runtime.factory import build_job_store
    from app.job_runtime.schemas import JobRequest

    store = build_job_store()
    record, created = store.submit(
        job_id="job-cutover",
        idempotency_key="submit-cutover",
        thread_id="thread-cutover",
        run_id="run-cutover",
        run_dir="/data/runs/run-cutover",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
    )
    assert created is True
    assert record.status == "queued"

    claim = store.claim_next(
        worker_id="worker-cutover",
        lease_seconds=30,
    )
    assert claim is not None
    assert claim.job.job_id == "job-cutover"

    done = store.mark_succeeded(
        job_id="job-cutover",
        claim_token=claim.claim_token,
        result={"final_status": "succeeded"},
        actor="worker-cutover",
    )
    assert done.status == "succeeded"

    events = store.list_events("job-cutover")
    event_types = [e.event_type for e in events]
    assert "job_submitted" in event_types
    assert "job_claimed" in event_types
    assert "job_succeeded" in event_types
