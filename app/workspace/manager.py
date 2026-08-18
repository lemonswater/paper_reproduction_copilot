from __future__ import annotations

from app.job_runtime.errors import LeaseLostError
from app.job_runtime.ports import JobStore
from app.job_runtime.process_reconcile import (
    workspace_portability_blockers,
)
from app.job_runtime.schemas import JobClaim, JobExecutionOutcome
from app.workspace.materializer import WorkspaceMaterializer
from app.workspace.schemas import WorkspaceBinding
from app.workspace.snapshot import WorkspaceSnapshotter


class WorkspaceManager:
    def __init__(
        self,
        *,
        store: JobStore,
        materializer: WorkspaceMaterializer,
        snapshotter: WorkspaceSnapshotter,
    ):
        self.store = store
        self.materializer = materializer
        self.snapshotter = snapshotter

    def prepare(self, claim: JobClaim) -> JobClaim:
        """claim 后、Graph 前执行；所有 DB 更新继续受 claim token fencing。"""

        job = claim.job
        manifest = self.store.get_workspace_manifest(
            job.workspace_manifest_id
        )
        if manifest.manifest_hash == "":
            raise ValueError("workspace manifest 缺少 hash")

        assignment_token = job.workspace_assignment_token
        if assignment_token is None:
            raise ValueError("claimed Job 缺少 workspace assignment token")

        planned = self.materializer.planned_binding(
            worker=claim.worker,
            manifest=manifest,
            requirements=job.requirements,
            assignment_epoch=job.workspace_assignment_epoch,
            assignment_token=assignment_token,
        )
        persisted = self.store.begin_workspace_assignment(
            job_id=job.job_id,
            claim_token=claim.claim_token,
            worker=claim.worker,
            manifest=manifest,
            assignment_token=assignment_token,
            workspace_root=planned.workspace_root,
            run_dir=planned.run_dir,
            repo_path=planned.repo_path,
            paper_path=planned.paper_path,
            log_path=planned.log_path,
        )

        try:
            self.materializer.materialize(
                manifest=manifest,
                binding=persisted,
            )
            ready = self.store.mark_workspace_ready(
                job_id=job.job_id,
                claim_token=claim.claim_token,
                assignment_token=assignment_token,
            )
        except Exception as exc:
            # 失败登记也受 fencing 保护；旧 Worker 丢 lease 时不能用登记失败
            # 覆盖新 Worker 的 assignment，同时不能让 LeaseLost 掩盖原始异常。
            try:
                self.store.fail_workspace_assignment(
                    job_id=job.job_id,
                    claim_token=claim.claim_token,
                    assignment_token=assignment_token,
                    reason=type(exc).__name__,
                )
            except LeaseLostError:
                pass
            raise

        return claim.model_copy(
            update={"workspace_binding": ready}
        )

    def seal_waiting(
        self,
        *,
        claim: JobClaim,
        outcome: JobExecutionOutcome,
    ) -> WorkspaceBinding:
        binding = claim.workspace_binding
        if binding is None:
            raise ValueError("seal 前缺少 workspace binding")

        state = dict(outcome.checkpoint_state)
        blockers = workspace_portability_blockers(
            run_dir=binding.run_dir,
            interrupt_nodes=[item.node for item in outcome.interrupts],
            state=state,
        )
        parent = self.store.get_workspace_manifest(
            claim.job.workspace_manifest_id
        )
        manifest = self.snapshotter.seal(
            job_id=claim.job.job_id,
            run_id=claim.job.run_id,
            run_dir=binding.run_dir,
            repo_path=binding.repo_path,
            paper_path=binding.paper_path,
            log_path=binding.log_path,
            parent=parent,
            source_host_id=claim.worker.host_id,
            source_worker_session_id=claim.worker.worker_session_id,
            artifact_records=outcome.artifact_records,
            external_data=parent.external_data,
            blocked_reasons=blockers,
        )
        affinity = (
            None if manifest.portable else claim.worker.host_id
        )
        self.store.seal_workspace_manifest(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            assignment_token=binding.assignment_token,
            manifest=manifest,
            affinity_host_id=affinity,
            actor=claim.worker.worker_id,
        )
        return binding
