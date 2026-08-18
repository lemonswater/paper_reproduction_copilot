"""Phase 26 shared test fixtures for workspace/worker/scheduling."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.job_runtime.schemas import (
    JobClaim,
    JobExecutionOutcome,
)
from app.workspace.repository import (
    workspace_manifest_hash,
)
from app.workspace.schemas import (
    JobRequirements,
    RepositoryIdentity,
    WorkerCapabilities,
    WorkerIdentity,
    WorkspaceBinding,
    WorkspaceManifest,
    WorkspaceSourcePaths,
)

POLICY_HASH = "a" * 64


def worker_fixture(
    *,
    worker_id: str = "worker-a",
    session_id: str = "session-a",
    host_id: str = "host-a",
    pool: str = "default",
    labels: list[str] | None = None,
    gpu_count: int = 0,
    cuda_major: int | None = None,
    workspace_root: str | None = None,
    profile_id: str = "local",
    policy_hash: str | None = None,
) -> WorkerIdentity:
    effective_hash = policy_hash or POLICY_HASH
    return WorkerIdentity(
        worker_id=worker_id,
        worker_session_id=session_id,
        host_id=host_id,
        pool=pool,
        workspace_root=(
            workspace_root
            or f"/data/workspaces/{host_id}"
        ),
        capabilities=WorkerCapabilities(
            execution_profile_ids=[profile_id],
            execution_backends=["local"],
            execution_policy_hashes={
                profile_id: effective_hash
            },
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            workspace_free_bytes=100 * 1024**3,
            gpu_count=gpu_count,
            cuda_major=cuda_major,
            labels=labels or [],
        ),
    )


def setup_local_execution_profile(
    tmp_path: Path,
    monkeypatch,
) -> str:
    """Create a temporary 'local' execution profile compatible with worker_fixture.

    Returns the policy_hash of the created profile so callers can pass it
    to worker_fixture(policy_hash=...) for a compatible worker.
    """

    from app.config import settings
    from app.execution.profile_store import (
        compute_execution_policy_hash,
    )
    from app.schemas import (
        ExecutionProfile,
        ResourceBudget,
    )

    root = tmp_path / "workspace-root"
    artifact = tmp_path / "artifact-root"
    root.mkdir(parents=True, exist_ok=True)
    artifact.mkdir(parents=True, exist_ok=True)

    # The profile validator requires artifact_root under allowed_root;
    # point allowed_root at tmp_path so test-local paths pass.
    monkeypatch.setattr(
        settings, "allowed_root", tmp_path
    )
    # Keep affinity consistent with worker_fixture default (host-a)
    monkeypatch.setattr(
        settings, "worker_host_id", "host-a"
    )

    profile = ExecutionProfile(
        profile_id="local",
        backend="local",
        workspace_root=str(root),
        artifact_root=str(artifact),
        budget=ResourceBudget(
            max_wall_time_seconds=3600,
            max_cpu_seconds=7200,
            max_memory_bytes=17179869184,
            max_processes=64,
            max_write_bytes=107374182400,
            max_gpu_memory_bytes=None,
            max_log_bytes_per_stream=16777216,
            max_preview_bytes=65536,
        ),
        network_policy="deny",
        enforcement_mode="best_effort",
        worker_pool="default",
        min_workspace_free_bytes=0,
        min_gpu_count=0,
        cuda_major=None,
        required_worker_labels=[],
    )

    profiles_file = tmp_path / "test-profiles.json"
    profiles_file.write_text(
        json.dumps({"profiles": [profile.model_dump()]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        settings,
        "execution_profiles_path",
        profiles_file,
    )
    monkeypatch.setattr(
        settings,
        "default_execution_profile",
        "local",
    )
    # API tests do not exercise model routing. Inject a bounded stub so their
    # temporary ALLOWED_ROOT cannot conflict with the project policy path.
    from app.model_routing import factory as model_factory

    monkeypatch.setattr(
        model_factory,
        "build_model_gateway",
        lambda: SimpleNamespace(
            ledger=SimpleNamespace(ping=lambda: "ready"),
        ),
    )
    return compute_execution_policy_hash(profile)


def requirements_fixture(
    *,
    profile_id: str = "local",
    pool: str = "default",
) -> JobRequirements:
    return JobRequirements(
        worker_pool=pool,
        execution_profile_id=profile_id,
        execution_policy_hash=POLICY_HASH,
        execution_backend="local",
    )


def manifest_fixture(
    *,
    suffix: str = "1",
    host_id: str = "host-a",
    portable: bool = False,
    job_id: str | None = None,
    run_id: str | None = None,
) -> WorkspaceManifest:
    actual_job_id = job_id or f"job-{suffix}"
    actual_run_id = run_id or f"run-{suffix}"
    draft = WorkspaceManifest(
        manifest_id=f"manifest-{suffix}",
        manifest_hash="",
        job_id=actual_job_id,
        run_id=actual_run_id,
        generation=0,
        source_host_id=host_id,
        entries=[],
        repository=RepositoryIdentity(
            commit_sha="b" * 40,
            branch="main",
            clean=False,
            bundle_logical_path=None,
        ),
        portable=portable,
        blocked_reasons=(
            [] if portable else ["contract-host-local"]
        ),
        source_paths=(
            None
            if portable
            else WorkspaceSourcePaths(
                repo_path="/data/repo",
                paper_path="/data/paper.pdf",
            )
        ),
        created_at=datetime.now(
            timezone.utc
        ).isoformat(),
    )
    return draft.model_copy(
        update={
            "manifest_hash": workspace_manifest_hash(
                draft
            )
        }
    )


def binding_fixture(
    *,
    suffix: str = "1",
    host_id: str = "host-a",
    worker_session_id: str = "session-a",
    job_id: str | None = None,
    run_id: str | None = None,
    manifest_id: str | None = None,
    manifest_hash: str | None = None,
    epoch: int = 1,
    status: str = "ready",
    run_dir: str | None = None,
    repo_path: str = "/data/repo",
    paper_path: str = "/data/paper.pdf",
) -> WorkspaceBinding:
    actual_job_id = job_id or f"job-{suffix}"
    actual_run_id = run_id or f"run-{suffix}"
    actual_manifest_id = manifest_id or f"manifest-{suffix}"
    actual_manifest_hash = (
        manifest_hash or "c" * 64
    )
    now = datetime.now(timezone.utc).isoformat()
    return WorkspaceBinding(
        assignment_id=f"was_{suffix}",
        assignment_epoch=epoch,
        assignment_token=f"wa_{suffix}",
        job_id=actual_job_id,
        run_id=actual_run_id,
        manifest_id=actual_manifest_id,
        manifest_hash=actual_manifest_hash,
        manifest_generation=0,
        worker_session_id=worker_session_id,
        host_id=host_id,
        workspace_root=f"/data/workspaces/{host_id}",
        run_dir=run_dir or f"/data/runs/{actual_run_id}",
        repo_path=repo_path,
        paper_path=paper_path,
        log_path=None,
        status=status,
        created_at=now,
        updated_at=now,
    )


def submit_to_store(
    store,
    *,
    suffix: str = "1",
    max_attempts: int = 3,
    now: float = 100.0,
    host_id: str = "host-a",
    portable: bool = False,
):
    """Shared helper: submit a Job with Phase 26 requirements + manifest."""
    return store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=f"/data/runs/run-{suffix}",
        request=_default_request(),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(
            suffix=suffix,
            host_id=host_id,
            portable=portable,
        ),
        max_attempts=max_attempts,
        now=now,
    )


def _default_request():
    from app.job_runtime.schemas import JobRequest

    return JobRequest(
        paper_path="/data/paper.pdf",
        repo_path="/data/repo",
        execution_profile_id="local",
    )


class PassThroughWorkspaceManager:
    """
    Minimal fake WorkspaceManager for tests that don't test
    materialization itself.
    """

    def __init__(self, binding: WorkspaceBinding):
        self.binding = binding
        self.seal_calls = 0

    def prepare(self, claim: JobClaim) -> JobClaim:
        return claim.model_copy(
            update={"workspace_binding": self.binding}
        )

    def seal_waiting(
        self,
        *,
        claim: JobClaim,
        outcome: JobExecutionOutcome,
    ) -> WorkspaceBinding:
        del claim, outcome
        self.seal_calls += 1
        return self.binding


class FakeWorkspaceSnapshotter:
    """
    Produces a minimal non-portable manifest without reading real files.
    For tests that exercise JobService.submit() without caring about
    workspace materialization.
    """

    def __init__(self, host_id: str = "test-host"):
        self.host_id = host_id
        self.calls = 0

    def snapshot_initial(
        self,
        *,
        job_id: str,
        run_id: str,
        paper_path: str,
        repo_path: str,
        log_path: str | None,
        source_host_id: str,
        external_data: list,
    ) -> WorkspaceManifest:
        self.calls += 1
        return manifest_fixture(
            suffix=job_id[-8:],
            host_id=source_host_id or self.host_id,
            job_id=job_id,
            run_id=run_id,
        )

    def seal(self, **kwargs):
        del kwargs
        raise NotImplementedError(
            "FakeWorkspaceSnapshotter.seal not implemented"
        )
