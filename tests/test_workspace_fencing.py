from __future__ import annotations

"""Phase 26 §51: Workspace fencing 测试。

验证 lease requeue 后旧 claim token 不能再 seal 新 manifest。
需要 ``TEST_DATABASE_URL``。
"""

import pytest

from app.job_runtime.errors import LeaseLostError
from app.job_runtime.postgres_store import PostgresJobStore
from app.workspace.repository import (
    workspace_manifest_hash,
)
from tests.job_store_contract import submit_fixture
from tests.workspace_helpers import worker_fixture

pytestmark = pytest.mark.postgres


def test_old_claim_cannot_publish_new_manifest(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    submit_fixture(store)
    worker = worker_fixture()
    store.register_worker(worker=worker, lease_seconds=30)
    claim = store.claim_next(worker=worker, lease_seconds=0)
    assert claim is not None

    parent = store.get_workspace_manifest(
        claim.job.workspace_manifest_id
    )
    token = claim.job.workspace_assignment_token
    assert token is not None

    store.begin_workspace_assignment(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        worker=worker,
        manifest=parent,
        assignment_token=token,
        workspace_root="/data/workspaces/host-a/job-1",
        run_dir="/data/runs/run-1",
        repo_path="/data/repo",
        paper_path="/data/paper.pdf",
        log_path=None,
    )
    store.mark_workspace_ready(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        assignment_token=token,
    )

    store.requeue_expired(
        job_id=claim.job.job_id,
        expired_claim_token=claim.claim_token,
        detail="test lease expiry",
        actor="test",
    )

    draft = parent.model_copy(
        update={
            "manifest_id": "manifest-stale",
            "manifest_hash": "",
            "generation": parent.generation + 1,
            "parent_manifest_id": parent.manifest_id,
        }
    )
    stale_manifest = draft.model_copy(
        update={
            "manifest_hash": workspace_manifest_hash(draft)
        }
    )

    with pytest.raises(LeaseLostError):
        store.seal_workspace_manifest(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            assignment_token=token,
            manifest=stale_manifest,
            affinity_host_id="host-a",
            actor="old-worker",
        )
