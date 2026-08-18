from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.job_runtime.schemas import (
    HeartbeatResult,
    JobClaim,
    JobEvent,
    JobInterrupt,
    JobRecord,
    JobRequest,
)
from app.observability.schemas import TraceCarrier
from app.workspace.schemas import (
    JobRequirements,
    WorkerIdentity,
    WorkerSession,
    WorkspaceBinding,
    WorkspaceManifest,
)


@runtime_checkable
class JobStore(Protocol):
    """Job Runtime 使用的完整持久化端口。"""

    def initialize(self) -> None:
        ...

    def ping(self) -> None:
        """连接后端并执行最小只读检查。"""
        ...

    def close(self) -> None:
        """释放当前进程拥有的连接池资源。"""
        ...

    def submit(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        thread_id: str,
        run_id: str,
        run_dir: str,
        request: JobRequest,
        requirements: JobRequirements,
        initial_manifest: WorkspaceManifest,
        max_attempts: int,
        submit_trace: TraceCarrier | None = None,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        ...

    def get(self, job_id: str) -> JobRecord:
        ...

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        ...

    def list_events(
        self,
        job_id: str,
        *,
        limit: int = 200,
    ) -> list[JobEvent]:
        ...

    def list_events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        ...

    def list_events_global_after(
        self,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """按全局 event_id 增序返回跨 Job 事件。"""
        ...

    def claim_next(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
        now: float | None = None,
    ) -> JobClaim | None:
        ...

    def register_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        ...

    def heartbeat_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        ...

    def drain_worker(
        self,
        *,
        worker_session_id: str,
    ) -> WorkerSession:
        ...

    def list_workers(
        self,
        *,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[WorkerSession]:
        ...

    def heartbeat(
        self,
        *,
        job_id: str,
        claim_token: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> HeartbeatResult:
        ...

    def mark_waiting(
        self,
        *,
        job_id: str,
        claim_token: str,
        interrupts: list[JobInterrupt],
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def mark_succeeded(
        self,
        *,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def mark_cancelled(
        self,
        *,
        job_id: str,
        claim_token: str,
        reason: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def mark_failed(
        self,
        *,
        job_id: str,
        claim_token: str,
        error: dict[str, Any],
        actor: str,
        retryable: bool = False,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def queue_resume(
        self,
        *,
        job_id: str,
        expected_node: str,
        value: Any,
        idempotency_key: str,
        actor: str,
        expected_job_version: int | None = None,
        expected_wait_generation: int | None = None,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        ...

    def request_cancel(
        self,
        *,
        job_id: str,
        reason: str,
        actor: str,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def list_expired_running(
        self,
        *,
        now: float | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        ...

    def requeue_expired(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def require_reconciliation(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        reconciliation: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def resolve_reconciliation(
        self,
        *,
        job_id: str,
        decision: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def get_workspace_manifest(
        self,
        manifest_id: str,
    ) -> WorkspaceManifest:
        ...

    def begin_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        worker: WorkerIdentity,
        manifest: WorkspaceManifest,
        assignment_token: str,
        workspace_root: str,
        run_dir: str,
        repo_path: str,
        paper_path: str,
        log_path: str | None,
    ) -> WorkspaceBinding:
        ...

    def mark_workspace_ready(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
    ) -> WorkspaceBinding:
        ...

    def fail_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        reason: str,
    ) -> WorkspaceBinding:
        ...

    def current_workspace_binding(
        self,
        job_id: str,
    ) -> WorkspaceBinding | None:
        ...

    def seal_workspace_manifest(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        manifest: WorkspaceManifest,
        affinity_host_id: str | None,
        actor: str,
    ) -> JobRecord:
        ...

    def list_workspace_gc_candidates(
        self,
        *,
        host_id: str,
        older_than: str,
        limit: int = 100,
    ) -> list[WorkspaceBinding]:
        ...

    def mark_workspace_garbage_collected(
        self,
        *,
        assignment_id: str,
        assignment_token: str,
        host_id: str,
    ) -> WorkspaceBinding:
        ...
