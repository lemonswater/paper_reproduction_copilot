from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.job_runtime.schemas import JobStatus
from app.schemas import (
    MAX_COMMAND_SELECTION_EDITS,
    CommandEdit,
)

DecisionKind = Literal[
    "command_selection",
    "action_approval",
    "patch_review",
    "patch_promotion",
]

OperationKind = Literal[
    "submit_decision",
    "cancel",
    "operator_reconciliation_required",
    "create_rerun_proposal",
]


class InteractionModel(BaseModel):
    """所有交互协议拒绝未知字段，避免拼错字段被静默忽略。"""

    model_config = ConfigDict(extra="forbid")


class JobCreateRequest(InteractionModel):
    """HTTP 提交体；thread_id 是运行身份，不放入 JobRequest。

    Phase 29：paper/repo 输入可以二选一提供本地路径或 resource_id，
    但每类必须且只能提供一个，避免混合身份漂移。
    """

    paper_path: str | None = None
    repo_path: str | None = None
    paper_resource_id: str | None = None
    repo_resource_id: str | None = None
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    log_path: str | None = None
    experiment_goal: str = "复现论文 main result"
    execution_profile_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_input_sources(self) -> JobCreateRequest:
        if (self.paper_path is None) == (
            self.paper_resource_id is None
        ):
            raise ValueError(
                "paper_path 与 paper_resource_id 必须且只能提供一个"
            )
        if (self.repo_path is None) == (
            self.repo_resource_id is None
        ):
            raise ValueError(
                "repo_path 与 repo_resource_id 必须且只能提供一个"
            )
        return self


class CommandSelectionDecision(InteractionModel):
    """公开 API 的命令选择协议；真正的范围和 stale 校验由 policy 完成。"""

    kind: Literal["command_selection"]
    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(
        default_factory=list,
        max_length=MAX_COMMAND_SELECTION_EDITS,
    )
    run_commands_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def reject_duplicate_edit_indexes(
        self,
    ) -> CommandSelectionDecision:
        indexes = [item.index for item in self.edits]
        if len(indexes) != len(set(indexes)):
            raise ValueError(
                "同一命令索引不能在一次 decision 中重复编辑"
            )
        return self


class ActionApprovalDecision(InteractionModel):
    kind: Literal["action_approval"]
    decision: Literal["approved", "rejected", "revise"]
    feedback: str | None = Field(
        default=None,
        max_length=4000,
    )


class PatchReviewDecision(InteractionModel):
    kind: Literal["patch_review"]
    decision: Literal["approved", "rejected", "revise"]
    feedback: str | None = Field(
        default=None,
        max_length=4000,
    )


class PatchPromotionDecision(InteractionModel):
    kind: Literal["patch_promotion"]
    decision: Literal["approved", "rejected"]
    feedback: str | None = Field(
        default=None,
        max_length=4000,
    )


# discriminator 让 FastAPI/Pydantic 根据 kind 选择唯一 schema。
Decision = Annotated[
    Union[
        CommandSelectionDecision,
        ActionApprovalDecision,
        PatchReviewDecision,
        PatchPromotionDecision,
    ],
    Field(discriminator="kind"),
]


class DecisionEnvelope(InteractionModel):
    """
    version 防止旧 Job 快照写入；
    wait_generation 防止旧 interrupt 输入写入新 interrupt。
    """

    expected_job_version: int = Field(ge=0)
    expected_wait_generation: int = Field(ge=1)
    decision: Decision


class CancelEnvelope(InteractionModel):
    expected_job_version: int = Field(ge=0)
    reason: str = Field(
        default="user requested cancellation",
        min_length=1,
        max_length=500,
    )


class PublicJobInput(InteractionModel):
    """
    响应只返回用户可理解的摘要。

    paper_path/repo_path/log_path 属于本机部署细节，不从 Job 查询接口返回。
    """

    paper_name: str
    repo_name: str
    experiment_goal: str
    execution_profile_id: str
    derived_from_job_id: str | None = None


class PublicInterrupt(InteractionModel):
    node: str
    interrupt_id: str | None = None
    value_preview: Any = None


class AllowedOperation(InteractionModel):
    operation_id: str
    kind: OperationKind
    endpoint: str | None = None
    decision_kind: DecisionKind | None = None
    expected_node: str | None = None
    expected_job_version: int
    expected_wait_generation: int | None = None
    allowed_decisions: list[str] = Field(
        default_factory=list
    )
    requires_idempotency_key: bool = True
    detail: str | None = None


class PublicJobResult(InteractionModel):
    final_status: str | None = None
    stage_error_count: int | None = None
    output_file_count: int | None = None


class JobView(InteractionModel):
    job_id: str
    thread_id: str
    run_id: str
    status: JobStatus
    version: int
    attempt_count: int
    max_attempts: int
    wait_generation: int
    interrupt_nodes: list[str] = Field(
        default_factory=list
    )
    interrupts: list[PublicInterrupt] = Field(
        default_factory=list
    )
    cancel_requested: bool
    cancellation_reason: str | None = None
    result: PublicJobResult | None = None
    error: Any = None
    reconciliation: Any = None
    input: PublicJobInput
    allowed_operations: list[AllowedOperation] = Field(
        default_factory=list
    )
    created_at: str
    updated_at: str


class JobMutationResponse(InteractionModel):
    job: JobView
    # submit/resume 可以精确返回是否重放；当前 cancel 兼容接口暂不返回该事实。
    replayed: bool | None = None


class JobListResponse(InteractionModel):
    items: list[JobView]
    count: int


class EventView(InteractionModel):
    event_id: int
    job_id: str
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(
        default_factory=dict
    )
    created_at: str


class EventPage(InteractionModel):
    items: list[EventView]
    next_after: int


class ArtifactView(InteractionModel):
    artifact_id: str
    run_id: str
    layer: str
    relative_path: str
    media_type: str
    sha256: str
    size_bytes: int
    producer_node: str
    created_at: str

    # 这是服务端能力声明，前端不自行猜测安全类型。
    preview_supported: bool = False

    integrity_status: Literal[
        "unchecked",
        "current",
    ] = "unchecked"


class ArtifactListResponse(InteractionModel):
    items: list[ArtifactView]
    count: int


class LogTailResponse(InteractionModel):
    relative_path: str | None = None
    content: str = ""
    lines: int
    truncated_by_bytes: bool = False


class ApiError(InteractionModel):
    code: str
    message: str
    request_id: str | None = None


TimelineRole = Literal["user", "assistant", "system"]
TimelineKind = Literal[
    "request",
    "progress",
    "decision",
    "result",
    "error",
]


class TimelineItem(InteractionModel):
    """前端可以稳定渲染的对话项，不包含内部 State 或绝对路径。"""

    item_id: str
    role: TimelineRole
    kind: TimelineKind
    title: str
    content: str
    created_at: str
    event_id: int | None = None
    operation: AllowedOperation | None = None
    interrupt: PublicInterrupt | None = None


class TimelineResponse(InteractionModel):
    job: JobView
    items: list[TimelineItem]
    last_event_id: int = 0


class PublicExecutionProfile(InteractionModel):
    profile_id: str
    backend: str
    enforcement_mode: str
    network_policy: str


class UiConfigResponse(InteractionModel):
    product_name: str
    default_execution_profile: str
    execution_profiles: list[PublicExecutionProfile]
    resources_enabled: bool = True
    deployment_mode: Literal["local_single_user"] = (
        "local_single_user"
    )
    chat_enabled: bool = False