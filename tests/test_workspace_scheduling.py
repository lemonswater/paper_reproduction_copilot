from __future__ import annotations

"""Phase 26 §50: PostgreSQL scheduling 测试。

验证 capability matching、host affinity 与 policy hash 校验在 SQL claim
层面的语义与 ``explain_compatibility()`` 一致。需要 ``TEST_DATABASE_URL``。
"""

import pytest

from app.job_runtime.postgres_store import PostgresJobStore
from app.job_runtime.schemas import JobRequest
from app.workspace.schemas import JobRequirements
from tests.workspace_helpers import (
    POLICY_HASH,
    manifest_fixture,
    worker_fixture,
)

pytestmark = pytest.mark.postgres


def _submit(
    store: PostgresJobStore,
    *,
    suffix: str,
    requirements: JobRequirements,
    source_host: str = "host-a",
) -> None:
    store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=f"/data/runs/run-{suffix}",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements,
        initial_manifest=manifest_fixture(
            suffix=suffix,
            host_id=source_host,
        ),
        max_attempts=3,
    )


def test_cpu_worker_skips_gpu_job_and_gpu_worker_claims(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    requirements = JobRequirements(
        worker_pool="gpu",
        execution_profile_id="local",
        execution_policy_hash=POLICY_HASH,
        execution_backend="local",
        min_gpu_count=1,
        cuda_major=11,
    )
    _submit(
        store,
        suffix="gpu",
        requirements=requirements,
        source_host="host-a",
    )

    cpu = worker_fixture(
        worker_id="cpu",
        session_id="cpu-session",
        host_id="host-a",
        pool="gpu",
    )
    gpu = worker_fixture(
        worker_id="gpu",
        session_id="gpu-session",
        host_id="host-a",
        pool="gpu",
        gpu_count=1,
        cuda_major=11,
    )
    store.register_worker(worker=cpu, lease_seconds=30)
    store.register_worker(worker=gpu, lease_seconds=30)

    assert store.claim_next(worker=cpu, lease_seconds=30) is None
    claim = store.claim_next(worker=gpu, lease_seconds=30)
    assert claim is not None
    assert claim.job.job_id == "job-gpu"


def test_host_affinity_blocks_other_host(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    requirements = JobRequirements(
        execution_profile_id="local",
        execution_policy_hash=POLICY_HASH,
        execution_backend="local",
    )
    _submit(
        store,
        suffix="affinity",
        requirements=requirements,
        source_host="host-a",
    )
    host_b = worker_fixture(
        worker_id="worker-b",
        session_id="session-b",
        host_id="host-b",
    )
    host_a = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
        host_id="host-a",
    )
    store.register_worker(worker=host_b, lease_seconds=30)
    store.register_worker(worker=host_a, lease_seconds=30)

    assert store.claim_next(worker=host_b, lease_seconds=30) is None
    assert store.claim_next(worker=host_a, lease_seconds=30) is not None


def test_policy_hash_mismatch_is_not_claimed(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    requirements = JobRequirements(
        execution_profile_id="local",
        execution_policy_hash="f" * 64,
        execution_backend="local",
    )
    _submit(
        store,
        suffix="policy",
        requirements=requirements,
        source_host="host-a",
    )
    worker = worker_fixture(host_id="host-a")
    store.register_worker(worker=worker, lease_seconds=30)
    assert store.claim_next(worker=worker, lease_seconds=30) is None
