"""Phase 35 核心服务：Plan/确认/预检/幂等 Sweep。"""
from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from app.job_runtime.errors import JobNotFoundError
from app.job_runtime.schemas import TERMINAL_JOB_STATUSES, JobRecord
from app.retention.errors import (
    RetentionBackendUnsupported,
    RetentionConflict,
    StorageCapacityExceeded,
)
from app.retention.inventory import StorageInventoryService
from app.retention.ports import (
    ArtifactRetentionPort,
    ChatRetentionPort,
    CheckpointRetentionPort,
    DeletableBlobStore,
    FailureMemoryRetentionPort,
    JobRetentionPort,
    KnowledgeMemoryRetentionPort,
    McpEvidenceRetentionPort,
    McpExportAuditRetentionPort,
    NotificationRetentionPort,
    PathRemover,
    ProjectMemoryRetentionPort,
    ResourceReferencePort,
    SweepLock,
)
from app.retention.repository import SqliteRetentionRepository
from app.retention.schemas import (
    BlobReference,
    CleanupPlan,
    CleanupResult,
    JobCleanupTarget,
    RetentionHold,
    RetentionPolicy,
    StorageSummary,
    StorageSummaryView,
    WorkspaceDeleteTarget,
)
from app.workspace.schemas import WorkspaceManifest


class _NoOpProjectMemoryRetentionPort:
    """Fallback when Project Memory is disabled."""

    def active_referenced_job_ids(self) -> set[str]:
        return set()


class _NoOpKnowledgeMemoryRetentionPort:
    def active_referenced_job_ids(self) -> set[str]:
        return set()


class _NoOpMcpEvidenceRetentionPort:
    def delete_for_job(self, job_id: str) -> int:
        del job_id
        return 0


class _NoOpMcpExportAuditRetentionPort:
    def delete_for_job(self, job_id: str) -> int:
        del job_id
        return 0

def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _workspace_blob_references(
    manifests: list[WorkspaceManifest],
    *,
    backend: str,
) -> list[BlobReference]:
    unique: dict[tuple[str, str], BlobReference] = {}
    for manifest in manifests:
        for entry in manifest.entries:
            candidate = BlobReference(
                backend=backend,
                object_key=entry.object_key,
                sha256=entry.sha256,
                size_bytes=entry.size_bytes,
            )
            key = (candidate.backend, candidate.object_key)
            previous = unique.get(key)
            if previous is not None and previous != candidate:
                raise RetentionConflict(
                    "同一 Workspace Blob key 对应不同内容身份"
                )
            unique[key] = candidate
    return sorted(
        unique.values(),
        key=lambda item: (item.backend, item.object_key),
    )

def _blob_map(
    references: list[BlobReference],
) -> dict[tuple[str, str], BlobReference]:
    result: dict[tuple[str, str], BlobReference] = {}
    for item in references:
        key = (item.backend, item.object_key)
        existing = result.get(key)
        if existing is not None and existing != item:
            raise RetentionConflict("同一 Blob key 的 size/hash 身份不一致")
        result[key] = item
    return result

class StorageQuotaGuard:
    """提交前容量保护；只拒绝新任务，不影响已有 Job。"""

    def __init__(self, inventory: StorageInventoryService):
        self.inventory = inventory

    def assert_can_submit(self) -> None:
        summary = self.inventory.summarize()
        if summary.pressure == "hard":
            raise StorageCapacityExceeded(
                "受管存储达到硬阈值或文件系统剩余空间不足；"
                "请先查看 /v1/storage/summary 并执行确认后的 GC"
            )

class RetentionService:
    def __init__(
        self,
        *,
        policy: RetentionPolicy,
        repository: SqliteRetentionRepository,
        jobs: JobRetentionPort,
        artifacts: ArtifactRetentionPort,
        chats: ChatRetentionPort,
        notifications: NotificationRetentionPort,
        resources: ResourceReferencePort,
        checkpoints: CheckpointRetentionPort,
        blob_store: DeletableBlobStore | None,
        path_remover: PathRemover,
        inventory: StorageInventoryService,
        selected_blob_backend: str,
        destructive_supported: bool,
        sweep_lock: SweepLock,
        failure_memory: FailureMemoryRetentionPort,
        project_memory: ProjectMemoryRetentionPort | None = None,
        knowledge_memory: KnowledgeMemoryRetentionPort | None = None,
        mcp_evidence: McpEvidenceRetentionPort | None = None,
        mcp_export_audit: McpExportAuditRetentionPort | None = None,
    ):
        self.policy = policy
        self.repository = repository
        self.jobs = jobs
        self.artifacts = artifacts
        self.chats = chats
        self.notifications = notifications
        self.resources = resources
        self.checkpoints = checkpoints
        self.blob_store = blob_store
        self.path_remover = path_remover
        self.inventory = inventory
        self.selected_blob_backend = selected_blob_backend
        self.destructive_supported = destructive_supported
        self.sweep_lock = sweep_lock
        self.failure_memory = failure_memory
        self.project_memory = project_memory or _NoOpProjectMemoryRetentionPort()
        self.knowledge_memory = (
            knowledge_memory or _NoOpKnowledgeMemoryRetentionPort()
        )
        self.mcp_evidence = (
            mcp_evidence or _NoOpMcpEvidenceRetentionPort()
        )
        self.mcp_export_audit = (
            mcp_export_audit
            or _NoOpMcpExportAuditRetentionPort()
        )
        self.repository.initialize()

    def storage_summary(self) -> StorageSummary:
        return self.inventory.summarize()

    def _blocked_job_ids(self) -> set[str]:
        return (
            self.repository.held_job_ids()
            | self.failure_memory.active_referenced_job_ids()
            | self.project_memory.active_referenced_job_ids()
            | self.knowledge_memory.active_referenced_job_ids()
        )

    def create_hold(self, *, job_id: str, reason: str, actor: str) -> RetentionHold:
        self.jobs.get(job_id)
        return self.repository.put_hold(
            job_id=job_id,
            reason=reason,
            actor=actor,
        )

    def delete_hold(self, job_id: str) -> bool:
        return self.repository.delete_hold(job_id)

    def list_holds(self) -> list[RetentionHold]:
        return self.repository.list_holds()

    def _target(self, job: JobRecord) -> JobCleanupTarget:
        bindings = self.jobs.list_workspace_bindings_for_retention(job.job_id)
        manifests = self.jobs.list_workspace_manifests_for_retention(job.job_id)
        paths = self.path_remover.validate_job_paths(job=job, bindings=bindings)

        workspace_targets = [
            WorkspaceDeleteTarget(
                path=str(Path(binding.workspace_root)),
                assignment_epoch=binding.assignment_epoch,
                assignment_token_sha256=_token_hash(binding.assignment_token),
                manifest_hash=binding.manifest_hash,
            )
            for binding in bindings
        ]
        artifact_blobs = self.artifacts.list_blob_references_for_job(job.job_id)
        workspace_blobs = _workspace_blob_references(
            manifests,
            backend=self.selected_blob_backend,
        )

        estimated = sum(
            item.size_bytes
            for item in _blob_map([*artifact_blobs, *workspace_blobs]).values()
        )
        return JobCleanupTarget(
            job_id=job.job_id,
            thread_id=job.thread_id,
            run_id=job.run_id,
            run_dir=job.run_dir,
            job_version=job.version,
            job_status=job.status,
            job_updated_at=job.updated_at,
            workspace_manifest_id=job.workspace_manifest_id,
            workspace_manifest_generation=job.workspace_manifest_generation,
            workspace_targets=workspace_targets,
            artifact_blobs=artifact_blobs,
            workspace_blobs=workspace_blobs,
            estimated_logical_bytes=estimated,
        )

    def create_plan(self) -> CleanupPlan:
        cutoff = time.time() - self.policy.job_retention_seconds
        held = self._blocked_job_ids()
        candidates = self.jobs.list_retention_candidates(
            updated_before=cutoff,
            limit=min(100, self.policy.max_jobs_per_plan * 4),
        )
        selected = [job for job in candidates if job.job_id not in held][
            : self.policy.max_jobs_per_plan
        ]

        created = datetime.now(timezone.utc)
        expires = created + timedelta(seconds=self.policy.plan_ttl_seconds)
        plan_id = f"gc_{uuid4().hex}"
        hash_payload = {
            "plan_id": plan_id,
            "policy": self.policy.model_dump(mode="json"),
            "targets": [self._target(job).model_dump(mode="json") for job in selected],
            "created_at": created.isoformat(),
            "expires_at": expires.isoformat(),
        }
        plan = CleanupPlan(
            **hash_payload,
            status="planned",
            plan_hash=_sha256(hash_payload),
        )
        return self.repository.create_plan(plan)

    def get_plan(self, plan_id: str) -> CleanupPlan:
        return self.repository.get_plan(plan_id)

    def confirm_plan(self, *, plan_id: str, plan_hash: str) -> CleanupPlan:
        return self.repository.confirm_plan(
            plan_id=plan_id,
            plan_hash=plan_hash,
        )

    def _assert_plan_hash(self, plan: CleanupPlan) -> None:
        payload = {
            "plan_id": plan.plan_id,
            "policy": plan.policy.model_dump(mode="json"),
            "targets": [item.model_dump(mode="json") for item in plan.targets],
            "created_at": plan.created_at,
            "expires_at": plan.expires_at,
        }
        if _sha256(payload) != plan.plan_hash:
            raise RetentionConflict("持久化 Plan payload 与 hash 不一致")

    def _assert_target_current(self, target: JobCleanupTarget) -> None:
        current = self.jobs.get(target.job_id)
        identity = (
            current.thread_id,
            current.run_id,
            current.run_dir,
            current.version,
            current.status,
            current.updated_at,
            current.workspace_manifest_id,
            current.workspace_manifest_generation,
        )
        expected = (
            target.thread_id,
            target.run_id,
            target.run_dir,
            target.job_version,
            target.job_status,
            target.job_updated_at,
            target.workspace_manifest_id,
            target.workspace_manifest_generation,
        )
        if identity != expected or current.status not in TERMINAL_JOB_STATUSES:
            raise RetentionConflict(f"Job 身份已变化：{target.job_id}")

        bindings = self.jobs.list_workspace_bindings_for_retention(target.job_id)
        paths = self.path_remover.validate_job_paths(job=current, bindings=bindings)
        planned_paths = {item.path for item in target.workspace_targets}
        current_workspace_paths = {item.workspace_root for item in bindings}
        if planned_paths != current_workspace_paths:
            raise RetentionConflict("Workspace target 集合已变化")

        current_tokens = {
            (item.assignment_epoch, _token_hash(item.assignment_token), item.manifest_hash)
            for item in bindings
        }
        planned_tokens = {
            (
                item.assignment_epoch,
                item.assignment_token_sha256,
                item.manifest_hash,
            )
            for item in target.workspace_targets
        }
        if current_tokens != planned_tokens:
            raise RetentionConflict("Workspace binding 身份已变化")

        del paths

        current_artifacts = self.artifacts.list_blob_references_for_job(target.job_id)
        current_manifests = self.jobs.list_workspace_manifests_for_retention(
            target.job_id
        )
        current_workspace_blobs = _workspace_blob_references(
            current_manifests,
            backend=self.selected_blob_backend,
        )
        if _blob_map(current_artifacts) != _blob_map(target.artifact_blobs):
            raise RetentionConflict("Artifact 引用快照已变化")
        if _blob_map(current_workspace_blobs) != _blob_map(target.workspace_blobs):
            raise RetentionConflict("Workspace Blob 引用快照已变化")

    def _preflight(self, plan: CleanupPlan) -> None:
        if not self.destructive_supported:
            raise RetentionBackendUnsupported(
                "第一版 Sweep 只支持 SQLite control plane + LocalBlobStore"
            )
        if self.policy.delete_local_blobs and self.blob_store is None:
            raise RetentionBackendUnsupported("当前 BlobStore 不支持安全删除")
        self._assert_plan_hash(plan)

        held = self._blocked_job_ids()
        for target in plan.targets:
            if any(
                blob.backend != self.selected_blob_backend
                for blob in [*target.artifact_blobs, *target.workspace_blobs]
            ):
                raise RetentionBackendUnsupported(
                    "Plan 含有非当前 LocalBlobStore 的历史 Blob；拒绝部分清理"
                )
            if target.job_id in held:
                raise RetentionConflict(f"Job 已被 retention hold：{target.job_id}")

            if self.repository.step_completed(
                plan_id=plan.plan_id,
                job_id=target.job_id,
                step_name="job_metadata",
            ):
                continue
            try:
                self._assert_target_current(target)
            except JobNotFoundError:
                prerequisites = (
                    "chat",
                    "notification",
                    "checkpoint",
                    "artifact_metadata",
                    "filesystem",
                )
                if not all(
                    self.repository.step_completed(
                        plan_id=plan.plan_id,
                        job_id=target.job_id,
                        step_name=name,
                    )
                    for name in prerequisites
                ):
                    raise RetentionConflict(
                        "Job 缺失但前置清理 journal 不完整，拒绝推断"
                    ) from None
                self.repository.record_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="job_metadata",
                    status="completed",
                    detail='{"inferred_after_crash":true}',
                )

    def _run_step(
        self,
        *,
        plan_id: str,
        job_id: str,
        step_name: str,
        operation,
    ) -> object | None:
        if self.repository.step_completed(
            plan_id=plan_id,
            job_id=job_id,
            step_name=step_name,
        ):
            return None
        try:
            value = operation()
            self.repository.record_step(
                plan_id=plan_id,
                job_id=job_id,
                step_name=step_name,
                status="completed",
                detail=_canonical({"result": value}),
            )
            return value
        except Exception as exc:
            self.repository.record_step(
                plan_id=plan_id,
                job_id=job_id,
                step_name=step_name,
                status="failed",
                detail=_canonical({"error_type": type(exc).__name__}),
            )
            raise

    def _remove_paths(self, target: JobCleanupTarget) -> int:
        job = self.jobs.get(target.job_id)
        bindings = self.jobs.list_workspace_bindings_for_retention(target.job_id)
        roots = self.path_remover.validate_job_paths(job=job, bindings=bindings)
        return sum(self.path_remover.remove_tree(path) for path in roots)

    def _live_blob_references(self, blob: BlobReference) -> int:
        return (
            self.artifacts.count_blob_references(
                backend=blob.backend,
                object_key=blob.object_key,
            )
            + self.jobs.count_workspace_blob_references(
                object_key=blob.object_key
            )
            + self.resources.count_blob_references(
                backend=blob.backend,
                object_key=blob.object_key,
            )
        )

    def _result_from_journal(self, plan: CleanupPlan) -> CleanupResult:
        steps = self.repository.list_steps(plan.plan_id)
        reclaimed = 0
        deleted_blobs = 0
        retained_shared = 0
        completed_jobs: set[str] = set()
        for step in steps:
            if step.status != "completed":
                continue
            detail = json.loads(step.detail or "{}")
            if step.step_name == "filesystem":
                value = detail.get("result")
                reclaimed += value if isinstance(value, int) else 0
            elif step.step_name == "job_metadata":
                completed_jobs.add(step.job_id)
            elif step.step_name.startswith("blob:"):
                if detail.get("deleted") is True:
                    deleted_blobs += 1
                    reclaimed += int(detail.get("size_bytes", 0))
                elif int(detail.get("live_references", 0)) > 0:
                    retained_shared += 1
        return CleanupResult(
            plan=plan,
            deleted_jobs=len(completed_jobs),
            deleted_blob_count=deleted_blobs,
            retained_shared_blob_count=retained_shared,
            reclaimed_logical_bytes=reclaimed,
            steps=steps,
        )

    def sweep(self, *, plan_id: str, plan_hash: str) -> CleanupResult:
        with self.sweep_lock.acquire():
            existing = self.repository.get_plan(plan_id)
            if existing.plan_hash != plan_hash:
                raise RetentionConflict("Plan hash 不匹配")
            if existing.status == "completed":
                return self._result_from_journal(existing)
            return self._sweep_locked(plan_id=plan_id, plan_hash=plan_hash)

    def _sweep_locked(
        self,
        *,
        plan_id: str,
        plan_hash: str,
    ) -> CleanupResult:
        plan = self.repository.claim_sweep(
            plan_id=plan_id,
            plan_hash=plan_hash,
        )
        try:
            self._preflight(plan)

            all_blobs = _blob_map(
                [
                    blob
                    for target in plan.targets
                    for blob in [*target.artifact_blobs, *target.workspace_blobs]
                ]
            )

            for target in plan.targets:
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="chat",
                    operation=lambda target=target: self.chats.delete_job_messages(
                        target.job_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="mcp_evidence",
                    operation=lambda target=target: self.mcp_evidence.delete_for_job(
                        target.job_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="mcp_export_audit",
                    operation=lambda target=target: (
                        self.mcp_export_audit.delete_for_job(
                            target.job_id
                        )
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="notification",
                    operation=lambda target=target: self.notifications.delete_for_job(
                        target.job_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="checkpoint",
                    operation=lambda target=target: self.checkpoints.delete_thread(
                        target.thread_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="artifact_metadata",
                    operation=lambda target=target: self.artifacts.delete_job_artifacts(
                        target.job_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="filesystem",
                    operation=lambda target=target: self._remove_paths(target),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="job_metadata",
                    operation=lambda target=target: self.jobs.delete_job_for_retention(
                        job_id=target.job_id,
                        expected_version=target.job_version,
                        expected_status=target.job_status,
                    ),
                )
            for blob in all_blobs.values():
                step_name = "blob:" + _sha256(
                    {"backend": blob.backend, "object_key": blob.object_key}
                )[:24]
                if self.repository.step_completed(
                    plan_id=plan.plan_id,
                    job_id="__global__",
                    step_name=step_name,
                ):
                    continue
                references = self._live_blob_references(blob)
                if references > 0 or not self.policy.delete_local_blobs:
                    self.repository.record_step(
                        plan_id=plan.plan_id,
                        job_id="__global__",
                        step_name=step_name,
                        status="completed",
                        detail=_canonical(
                            {
                                "deleted": False,
                                "live_references": references,
                                "size_bytes": blob.size_bytes,
                            }
                        ),
                    )
                    continue

                assert self.blob_store is not None
                removed = self.blob_store.delete_if_matches(
                    object_key=blob.object_key,
                    expected_sha256=blob.sha256,
                    expected_size=blob.size_bytes,
                )
                self.repository.record_step(
                    plan_id=plan.plan_id,
                    job_id="__global__",
                    step_name=step_name,
                    status="completed",
                    detail=_canonical(
                        {
                            "deleted": removed,
                            "live_references": 0,
                            "size_bytes": blob.size_bytes,
                        }
                    ),
                )

            completed = self.repository.finish_plan(plan_id=plan.plan_id)
            return self._result_from_journal(completed)
        except Exception as exc:
            self.repository.fail_plan(
                plan_id=plan.plan_id,
                code=type(exc).__name__,
            )
            raise