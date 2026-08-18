"""Retention Schemas 定义。"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class RetentionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class RetentionPolicy(RetentionModel):
    job_retention_seconds: int = Field(ge=0)
    max_jobs_per_plan: int = Field(ge=1, le=100)
    plan_ttl_seconds: int = Field(ge=60)
    delete_local_blobs: bool = True

class ManagedRootUsage(RetentionModel):
    name: str
    path: str
    exists: bool
    logical_bytes: int = Field(ge=0)
    allocated_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    skipped_symlink_count: int = Field(ge=0)
    error_count: int = Field(ge=0)

class StorageSummary(RetentionModel):
    generated_at: str
    managed_logical_bytes: int = Field(ge=0)
    managed_allocated_bytes: int = Field(ge=0)
    filesystem_total_bytes: int = Field(ge=0)
    filesystem_free_bytes: int = Field(ge=0)
    soft_limit_bytes: int = Field(ge=0)
    hard_limit_bytes: int = Field(ge=0)
    min_free_bytes: int = Field(ge=0)
    pressure: Literal["normal", "soft", "hard"]
    destructive_gc_supported: bool
    roots: list[ManagedRootUsage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class ManagedRootUsageView(RetentionModel):
    name: str
    exists: bool
    logical_bytes: int = Field(ge=0)
    allocated_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    skipped_symlink_count: int = Field(ge=0)
    error_count: int = Field(ge=0)

class StorageSummaryView(RetentionModel):
    generated_at: str
    managed_logical_bytes: int
    managed_allocated_bytes: int
    filesystem_total_bytes: int
    filesystem_free_bytes: int
    soft_limit_bytes: int
    hard_limit_bytes: int
    min_free_bytes: int
    pressure: Literal["normal", "soft", "hard"]
    destructive_gc_supported: bool
    roots: list[ManagedRootUsageView]
    warnings: list[str]

    @classmethod
    def from_summary(cls, summary: StorageSummary) -> "StorageSummaryView":
        payload = summary.model_dump(exclude={"roots", "warnings"})
        return cls(
            **payload,
            roots=[
                ManagedRootUsageView(
                    **item.model_dump(exclude={"path"})
                )
                for item in summary.roots
            ],
            warnings=(
                [f"{len(summary.warnings)} inventory warnings; inspect CLI"]
                if summary.warnings
                else []
            ),
        )

class BlobReference(RetentionModel):
    backend: str
    object_key: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)

class WorkspaceDeleteTarget(RetentionModel):
    path: str
    assignment_epoch: int = Field(ge=0)
    assignment_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

class JobCleanupTarget(RetentionModel):
    job_id: str
    thread_id: str
    run_id: str
    run_dir: str
    job_version: int = Field(ge=0)
    job_status: Literal["succeeded", "failed", "cancelled"]
    job_updated_at: str
    workspace_manifest_id: str
    workspace_manifest_generation: int = Field(ge=0)
    workspace_targets: list[WorkspaceDeleteTarget] = Field(
        default_factory=list
    )
    artifact_blobs: list[BlobReference] = Field(default_factory=list)
    workspace_blobs: list[BlobReference] = Field(default_factory=list)
    estimated_logical_bytes: int = Field(ge=0)

class CleanupPlan(RetentionModel):
    plan_id: str
    status: Literal[
        "planned",
        "confirmed",
        "sweeping",
        "completed",
        "failed",
    ]
    plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: RetentionPolicy
    targets: list[JobCleanupTarget]
    created_at: str
    expires_at: str
    confirmed_at: str | None = None
    completed_at: str | None = None
    failure_code: str | None = None

class CleanupStep(RetentionModel):
    plan_id: str
    job_id: str
    step_name: str
    status: Literal["pending", "completed", "failed"]
    detail: str | None = None
    updated_at: str

class CleanupResult(RetentionModel):
    plan: CleanupPlan
    deleted_jobs: int = Field(ge=0)
    deleted_blob_count: int = Field(ge=0)
    retained_shared_blob_count: int = Field(ge=0)
    reclaimed_logical_bytes: int = Field(ge=0)
    steps: list[CleanupStep] = Field(default_factory=list)

class CleanupTargetView(RetentionModel):
    job_id: str
    run_id: str
    job_status: Literal["succeeded", "failed", "cancelled"]
    job_updated_at: str
    estimated_logical_bytes: int = Field(ge=0)

class CleanupPlanView(RetentionModel):
    plan_id: str
    status: str
    plan_hash: str
    targets: list[CleanupTargetView]
    created_at: str
    expires_at: str
    failure_code: str | None = None

    @classmethod
    def from_plan(cls, plan: CleanupPlan) -> "CleanupPlanView":
        return cls(
            plan_id=plan.plan_id,
            status=plan.status,
            plan_hash=plan.plan_hash,
            targets=[
                CleanupTargetView(
                    job_id=item.job_id,
                    run_id=item.run_id,
                    job_status=item.job_status,
                    job_updated_at=item.job_updated_at,
                    estimated_logical_bytes=item.estimated_logical_bytes,
                )
                for item in plan.targets
            ],
            created_at=plan.created_at,
            expires_at=plan.expires_at,
            failure_code=plan.failure_code,
        )

class CleanupResultView(RetentionModel):
    plan: CleanupPlanView
    deleted_jobs: int = Field(ge=0)
    deleted_blob_count: int = Field(ge=0)
    retained_shared_blob_count: int = Field(ge=0)
    reclaimed_logical_bytes: int = Field(ge=0)

    @classmethod
    def from_result(cls, result: CleanupResult) -> "CleanupResultView":
        return cls(
            plan=CleanupPlanView.from_plan(result.plan),
            deleted_jobs=result.deleted_jobs,
            deleted_blob_count=result.deleted_blob_count,
            retained_shared_blob_count=result.retained_shared_blob_count,
            reclaimed_logical_bytes=result.reclaimed_logical_bytes,
        )

class RetentionHold(RetentionModel):
    job_id: str
    reason: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=200)
    created_at: str

class PlanConfirmRequest(RetentionModel):
    plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

class HoldRequest(RetentionModel):
    reason: str = Field(min_length=1, max_length=500)
