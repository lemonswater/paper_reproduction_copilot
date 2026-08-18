from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SHA256 = r"^[0-9a-f]{64}$"

ProjectStatus = Literal["active", "archived"]
ProjectFactStatus = Literal[
    "proposed",
    "confirmed",
    "superseded",
    "revoked",
    "expired",
    "deleted",
]
ProjectFactAuthority = Literal[
    "unconfirmed_proposal",
    "explicit_user",
]
ProjectFactCategory = Literal[
    "user_constraint",
    "dataset_binding",
    "execution_default",
    "reproduction_goal",
    "build_prerequisite",
    "project_note",
]


class ProjectMemoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectAnchor(ProjectMemoryModel):
    """项目创建时冻结的可信 Job/Workspace 身份。"""

    job_id: str = Field(min_length=1, max_length=200)
    job_version: int = Field(ge=0)
    run_id: str = Field(min_length=1, max_length=300)
    workspace_manifest_id: str = Field(min_length=1, max_length=300)
    workspace_manifest_hash: str = Field(pattern=SHA256)
    paper_sha256: str = Field(pattern=SHA256)
    repository_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    repository_clean: bool


class ProjectRecord(ProjectMemoryModel):
    schema_version: Literal["phase46-v1"] = "phase46-v1"
    project_id: str = Field(pattern=r"^project_[0-9a-f]{24}$")
    display_name: str = Field(min_length=1, max_length=200)
    status: ProjectStatus
    anchor: ProjectAnchor
    version: int = Field(ge=0)
    record_hash: str = Field(pattern=SHA256)
    created_by: str = Field(min_length=1, max_length=200)
    created_at: str
    updated_at: str
    archived_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_archive_shape(self) -> "ProjectRecord":
        if self.status == "archived" and not self.archived_reason:
            raise ValueError("archived project 必须说明原因")
        if self.status == "active" and self.archived_reason is not None:
            raise ValueError("active project 不能携带 archived_reason")
        return self


class ProjectJobBinding(ProjectMemoryModel):
    project_id: str = Field(pattern=r"^project_[0-9a-f]{24}$")
    job_id: str = Field(min_length=1, max_length=200)
    job_version_at_binding: int = Field(ge=0)
    run_id: str = Field(min_length=1, max_length=300)
    workspace_manifest_id: str = Field(min_length=1, max_length=300)
    workspace_manifest_hash: str = Field(pattern=SHA256)
    paper_sha256: str = Field(pattern=SHA256)
    repository_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    role: Literal["anchor", "member"]
    bound_by: str = Field(min_length=1, max_length=200)
    bound_at: str


class TextFactValue(ProjectMemoryModel):
    kind: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=2000)


class BooleanFactValue(ProjectMemoryModel):
    kind: Literal["boolean"] = "boolean"
    value: bool


class DatasetBindingFactValue(ProjectMemoryModel):
    """只保存 Worker Capability label，不泄露本机数据根路径。"""

    kind: Literal["dataset_binding"] = "dataset_binding"
    dataset_name: str = Field(min_length=1, max_length=200)
    required_worker_label: str = Field(min_length=1, max_length=200)
    fingerprint: str | None = Field(default=None, max_length=300)


class ExecutionProfileFactValue(ProjectMemoryModel):
    """fingerprint/policy_hash 必须由服务端读取真实 Profile 后写入。"""

    kind: Literal["execution_profile"] = "execution_profile"
    profile_id: str = Field(min_length=1, max_length=200)
    profile_fingerprint: str = Field(pattern=SHA256)
    execution_policy_hash: str = Field(pattern=SHA256)


ProjectFactValue = Annotated[
    Union[
        TextFactValue,
        BooleanFactValue,
        DatasetBindingFactValue,
        ExecutionProfileFactValue,
    ],
    Field(discriminator="kind"),
]


class ExecutionProfileDraftValue(ProjectMemoryModel):
    """API Draft 只接受 profile_id，不接受调用方自报 Hash。"""

    kind: Literal["execution_profile"] = "execution_profile"
    profile_id: str = Field(min_length=1, max_length=200)


ProjectFactDraftValue = Annotated[
    Union[
        TextFactValue,
        BooleanFactValue,
        DatasetBindingFactValue,
        ExecutionProfileDraftValue,
    ],
    Field(discriminator="kind"),
]


def _normalized_key(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    if not normalized:
        raise ValueError("fact key 不能为空")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._:-")
    if any(char not in allowed for char in normalized):
        raise ValueError(
            "fact key 只能包含小写字母、数字、点、下划线、冒号和连字符"
        )
    return normalized


class ProjectFactContent(ProjectMemoryModel):
    category: ProjectFactCategory
    key: str = Field(min_length=1, max_length=200)
    value: ProjectFactValue

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalized_key(value)

    @model_validator(mode="after")
    def validate_category_value(self) -> "ProjectFactContent":
        if self.category == "dataset_binding":
            if not isinstance(self.value, DatasetBindingFactValue):
                raise ValueError("dataset_binding 必须使用 dataset_binding value")
        elif self.category == "execution_default":
            if not isinstance(self.value, ExecutionProfileFactValue):
                raise ValueError("execution_default 必须使用 execution_profile value")
        elif not isinstance(self.value, (TextFactValue, BooleanFactValue)):
            raise ValueError(f"{self.category} 只能使用 text/boolean value")
        return self


class ProjectFactDraftContent(ProjectMemoryModel):
    category: ProjectFactCategory
    key: str = Field(min_length=1, max_length=200)
    value: ProjectFactDraftValue

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalized_key(value)


class ManualUserFactSource(ProjectMemoryModel):
    kind: Literal["manual_user"] = "manual_user"
    actor: str = Field(min_length=1, max_length=200)
    source_note: str = Field(min_length=1, max_length=1000)
    request_sha256: str = Field(pattern=SHA256)


class ChatUserMessageFactSource(ProjectMemoryModel):
    kind: Literal["chat_user_message"] = "chat_user_message"
    actor: str = Field(min_length=1, max_length=200)
    job_id: str = Field(min_length=1, max_length=200)
    message_id: str = Field(min_length=1, max_length=300)
    message_sequence: int = Field(ge=1)
    message_sha256: str = Field(pattern=SHA256)


ProjectFactSource = Annotated[
    Union[ManualUserFactSource, ChatUserMessageFactSource],
    Field(discriminator="kind"),
]


class ProjectFactConfirmation(ProjectMemoryModel):
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    confirmed_at: str


class ProjectFactTerminalEvent(ProjectMemoryModel):
    status: Literal["superseded", "revoked", "expired", "deleted"]
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    occurred_at: str


class ProjectFactRecord(ProjectMemoryModel):
    schema_version: Literal["phase46-v1"] = "phase46-v1"
    fact_id: str = Field(pattern=r"^fact_[0-9a-f]{24}$")
    project_id: str = Field(pattern=r"^project_[0-9a-f]{24}$")
    version: int = Field(ge=0)
    status: ProjectFactStatus
    authority: ProjectFactAuthority

    # deleted tombstone 的 content 为 None，但 content_hash 永远保留。
    content: ProjectFactContent | None
    content_hash: str = Field(pattern=SHA256)
    source: ProjectFactSource
    confirmation: ProjectFactConfirmation | None = None
    terminal_event: ProjectFactTerminalEvent | None = None
    # delete 不覆盖先前的 revoke/expire/supersede 审计事件。
    prior_terminal_events: list[ProjectFactTerminalEvent] = Field(
        default_factory=list,
        max_length=16,
    )

    supersedes_fact_id: str | None = Field(
        default=None,
        pattern=r"^fact_[0-9a-f]{24}$",
    )
    supersedes_record_hash: str | None = Field(default=None, pattern=SHA256)
    superseded_by_fact_id: str | None = Field(
        default=None,
        pattern=r"^fact_[0-9a-f]{24}$",
    )

    expires_at: str | None = None
    created_at: str
    updated_at: str
    record_hash: str = Field(pattern=SHA256)

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> "ProjectFactRecord":
        if self.status == "proposed":
            if self.authority != "unconfirmed_proposal":
                raise ValueError("proposed authority 必须是 unconfirmed_proposal")
            if self.confirmation is not None or self.terminal_event is not None:
                raise ValueError("proposed 不能已有确认或终态事件")
        elif self.status == "confirmed":
            if self.authority != "explicit_user" or self.confirmation is None:
                raise ValueError("confirmed 必须有 explicit_user confirmation")
            if self.terminal_event is not None:
                raise ValueError("confirmed 不能已有终态事件")
        else:
            if self.terminal_event is None:
                raise ValueError("终态 fact 必须记录 terminal_event")
            if self.terminal_event.status != self.status:
                raise ValueError("terminal_event.status 必须等于当前 status")

        if self.status == "deleted":
            if self.content is not None:
                raise ValueError("deleted tombstone 不能保留 content")
        elif self.content is None:
            raise ValueError("非 deleted fact 必须保留 content")

        supersedes = self.supersedes_fact_id is not None
        if supersedes != (self.supersedes_record_hash is not None):
            raise ValueError("supersedes id/hash 必须同时出现")
        if self.status == "superseded" and self.superseded_by_fact_id is None:
            raise ValueError("superseded fact 必须指向 successor")
        return self


class ProjectCreateRequest(ProjectMemoryModel):
    display_name: str = Field(min_length=1, max_length=200)
    anchor_job_id: str = Field(min_length=1, max_length=200)
    expected_anchor_job_version: int = Field(ge=0)
    expected_workspace_manifest_hash: str = Field(pattern=SHA256)


class ProjectBindJobRequest(ProjectMemoryModel):
    job_id: str = Field(min_length=1, max_length=200)
    expected_job_version: int = Field(ge=0)
    expected_workspace_manifest_hash: str = Field(pattern=SHA256)


class ManualFactProposalRequest(ProjectMemoryModel):
    content: ProjectFactDraftContent
    source_note: str = Field(min_length=1, max_length=1000)
    expires_at: str | None = None


class ChatFactProposalRequest(ProjectMemoryModel):
    source_job_id: str = Field(min_length=1, max_length=200)
    source_message_sequence: int = Field(ge=1)
    expected_message_id: str = Field(min_length=1, max_length=300)
    expected_message_sha256: str = Field(pattern=SHA256)
    content: ProjectFactDraftContent
    expires_at: str | None = None


class FactConfirmRequest(ProjectMemoryModel):
    expected_version: int = Field(ge=0)
    expected_record_hash: str = Field(pattern=SHA256)
    reason: str = Field(min_length=1, max_length=1000)


class FactCorrectRequest(ProjectMemoryModel):
    expected_version: int = Field(ge=0)
    expected_record_hash: str = Field(pattern=SHA256)
    content: ProjectFactDraftContent
    reason: str = Field(min_length=1, max_length=1000)
    expires_at: str | None = None


class FactTerminalRequest(ProjectMemoryModel):
    expected_version: int = Field(ge=0)
    expected_record_hash: str = Field(pattern=SHA256)
    reason: str = Field(min_length=1, max_length=1000)


class ProjectArchiveRequest(ProjectMemoryModel):
    expected_version: int = Field(ge=0)
    expected_record_hash: str = Field(pattern=SHA256)
    reason: str = Field(min_length=1, max_length=1000)


class ProjectMutationResponse(ProjectMemoryModel):
    project: ProjectRecord
    replayed: bool = False


class ProjectFactMutationResponse(ProjectMemoryModel):
    fact: ProjectFactRecord
    replayed: bool = False


class ProjectFactCorrectionResponse(ProjectMemoryModel):
    previous: ProjectFactRecord
    successor: ProjectFactRecord
    replayed: bool = False


class ProjectFactPackItem(ProjectMemoryModel):
    fact_id: str
    fact_hash: str = Field(pattern=SHA256)
    category: ProjectFactCategory
    key: str
    value: ProjectFactValue
    authority: Literal["explicit_user"] = "explicit_user"
    source_kind: Literal["manual_user", "chat_user_message"]
    expires_at: str | None = None


class ProjectFactPack(ProjectMemoryModel):
    project_id: str = Field(pattern=r"^project_[0-9a-f]{24}$")
    project_hash: str = Field(pattern=SHA256)
    items: list[ProjectFactPackItem] = Field(default_factory=list)
    pack_hash: str = Field(pattern=SHA256)
    generated_at: str
