from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from app.observability.schemas import TraceCarrier
from app.rerun.schemas import DerivedRunInput
from app.schemas import ArtifactRecord
from app.workspace.schemas import (
    ExternalDataReference,
    JobRequirements,
    WorkerIdentity,
    WorkspaceBinding,
)

JobStatus = Literal[
    "queued",
    "running",
    "waiting_for_input",
    "cancelling",
    "succeeded",
    "failed",
    "cancelled",
    "reconciliation_required",
]

TERMINAL_JOB_STATUSES = {
    "succeeded",
    "failed",
    "cancelled",
}

WAITABLE_JOB_STATUSES = {
    *TERMINAL_JOB_STATUSES,
    "waiting_for_input",
    "reconciliation_required",
}


class JobModel(BaseModel):
    """Job Runtime 的所有持久化对象都拒绝未知字段。"""

    model_config = ConfigDict(extra="forbid")


class ResolvedResourceInput(JobModel):
    """Job 冻结的不可变 Resource manifest snapshot。

    不只保存 resource_id 后动态读取最新 Resource；metadata 被修正后
    旧 Job 的输入身份不能漂移。
    """

    resource_id: str
    manifest_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    object_key: str
    content_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    size_bytes: int = Field(ge=0)
    kind: str
    git_commit: str | None = None


class JobRequest(JobModel):
    """提交任务所需的业务输入，不保存 API key 或完整 Prompt。

    Phase 29：paper/repo 本地兼容字段改为 optional，同时支持
    paper_resource/repo_resource 引用 published Resource。
    Phase 39：增加 derived_run 模式，从可信父 Run 派生新 Job。
    """

    paper_path: str | None = None
    repo_path: str | None = None
    paper_resource: ResolvedResourceInput | None = None
    repo_resource: ResolvedResourceInput | None = None
    derived_run: DerivedRunInput | None = None
    log_path: str | None = None
    experiment_goal: str = "复现论文 main result"
    execution_profile_id: str = Field(min_length=1)
    # Phase 26：外部数据集只保存引用与可达性要求，不内联内容。
    dataset_refs: list[ExternalDataReference] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_input_sources(self) -> "JobRequest":
        standard_complete = (
            self.derived_run is None
            and (self.paper_path is None)
            != (self.paper_resource is None)
            and (self.repo_path is None)
            != (self.repo_resource is None)
        )
        derived_complete = (
            self.derived_run is not None
            and self.paper_path is None
            and self.repo_path is None
            and self.paper_resource is None
            and self.repo_resource is None
            and self.log_path is None
        )
        if sum((standard_complete, derived_complete)) != 1:
            raise ValueError(
                "JobRequest 必须为 paper/repo 各选择一个本地或 Resource 输入，"
                "或者完整选择 derived_run 输入"
            )
        return self


class JobInterrupt(JobModel):
    """
    Job Store 只保存 interrupt 的节点身份和有界 preview。

    完整业务状态仍由 LangGraph checkpoint 保存。
    """

    node: str
    interrupt_id: str | None = None
    value_preview: Any = None


class JobResumeRequest(JobModel):
    resume_id: str
    job_id: str
    wait_generation: int = Field(ge=1)
    idempotency_key: str
    expected_node: str
    value: Any
    value_hash: str
    status: Literal["pending", "consumed"]
    created_at: str
    consumed_at: str | None = None


class JobRecord(JobModel):
    job_id: str
    idempotency_key: str
    request_hash: str

    thread_id: str
    run_id: str
    run_dir: str
    request: JobRequest

    # Phase 26 调度与 workspace pointer。
    requirements: JobRequirements
    affinity_host_id: str | None = None
    workspace_manifest_id: str
    workspace_manifest_generation: int = Field(ge=0)
    workspace_assignment_epoch: int = Field(ge=0)

    status: JobStatus
    version: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    wait_generation: int = Field(ge=0)

    worker_id: str | None = None
    worker_session_id: str | None = None
    worker_host_id: str | None = None
    claim_token: str | None = None
    workspace_assignment_token: str | None = None
    claimed_at: str | None = None
    heartbeat_at: str | None = None
    lease_expires_at: str | None = None
    available_at: str

    interrupt_nodes: list[str] = Field(
        default_factory=list
    )
    interrupts: list[JobInterrupt] = Field(
        default_factory=list
    )
    pending_resume_id: str | None = None

    cancel_requested: bool = False
    cancellation_reason: str | None = None

    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    reconciliation: dict[str, Any] | None = None

    submit_trace: TraceCarrier | None = None

    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def validate_ownership(self) -> JobRecord:
        owned = self.status in {
            "running",
            "cancelling",
        }
        ownership = (
            self.worker_id,
            self.worker_session_id,
            self.worker_host_id,
            self.claim_token,
            self.workspace_assignment_token,
            self.claimed_at,
            self.heartbeat_at,
            self.lease_expires_at,
        )
        if owned and any(value is None for value in ownership):
            raise ValueError(
                "running/cancelling Job 必须有完整 ownership"
            )
        return self


class JobClaim(JobModel):
    """worker 本次 claim 的不可变快照。"""

    job: JobRecord
    claim_token: str
    worker: WorkerIdentity
    resume_request: JobResumeRequest | None = None
    workspace_binding: WorkspaceBinding | None = None


class HeartbeatResult(JobModel):
    lease_renewed: bool
    cancel_requested: bool
    cancellation_reason: str | None = None
    lease_expires_at: str


class JobExecutionOutcome(JobModel):
    status: Literal[
        "succeeded",
        "waiting_for_input",
        "cancelled",
    ]
    result: dict[str, Any] = Field(
        default_factory=dict
    )
    interrupts: list[JobInterrupt] = Field(
        default_factory=list
    )
    artifact_records: list[
        ArtifactRecord
    ] = Field(default_factory=list)
    # 仅进程内使用，不写入持久 result_json。
    checkpoint_state: dict[str, Any] = Field(
        default_factory=dict,
        exclude=True,
    )


class JobEvent(JobModel):
    event_id: int
    job_id: str
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ReconcileDecision(JobModel):
    disposition: Literal[
        "safe_to_requeue",
        "active_process",
        "ambiguous_process",
        "finished_process_without_checkpoint",
    ]
    detail: str
    process_records: list[dict[str, Any]] = Field(
        default_factory=list
    )
