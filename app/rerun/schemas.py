# app/rerun/schemas.py
from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

SHA256 = r"^[0-9a-f]{64}$"
PROPOSAL_ID = r"^rerun_[0-9a-f]{24}$"


class RerunModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RerunArgumentEdit(RerunModel):
    """第一版只编辑已经存在的 GNU-style 长选项。"""

    option: str = Field(pattern=r"^--[A-Za-z0-9][A-Za-z0-9_-]*$")
    operation: Literal["set", "remove"]
    expected_old_value: str | None = Field(default=None, max_length=2000)
    value: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_operation(self) -> "RerunArgumentEdit":
        if self.operation == "set":
            if self.expected_old_value is None:
                raise ValueError("set 必须声明 expected_old_value")
            if self.value is None:
                raise ValueError("set 必须提供 value")
        elif self.value is not None:
            raise ValueError("remove 不能提供 value")
        return self


class RerunTemplateArg(RerunModel):
    kind: Literal[
        "literal",
        "repo_path",
        "run_path",
        "dataset_path",
    ]
    value: str | None = Field(default=None, max_length=2000)
    relative_path: str | None = Field(default=None, max_length=1000)
    dataset_label: str | None = Field(default=None, max_length=200)

    @field_validator("value")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("template literal 不能为空")
        if value is not None and any(
            char in value for char in ("\x00", "\n", "\r")
        ):
            raise ValueError("template literal 不能包含控制字符")
        return value

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.startswith("/") or "\\" in value:
            raise ValueError("template path 必须是 POSIX 相对路径")
        parts = value.split("/")
        if any(part in {"", ".."} for part in parts):
            raise ValueError("template path 不能包含空段或 ..")
        return value

    @model_validator(mode="after")
    def validate_shape(self) -> "RerunTemplateArg":
        if self.kind == "literal":
            if self.value is None:
                raise ValueError("literal arg 缺少 value")
            if self.relative_path is not None or self.dataset_label is not None:
                raise ValueError("literal arg 不能包含路径模板字段")
        elif self.kind in {"repo_path", "run_path"}:
            if self.relative_path is None:
                raise ValueError("repo/run path arg 缺少 relative_path")
            if self.value is not None or self.dataset_label is not None:
                raise ValueError("repo/run path arg 字段组合非法")
        else:
            if self.relative_path is None or self.dataset_label is None:
                raise ValueError("dataset_path arg 缺少 label 或 relative_path")
            if not self.dataset_label.strip():
                raise ValueError("dataset_path label 不能为空")
            if self.value is not None:
                raise ValueError("dataset_path arg 不能包含 literal value")
        return self


class RerunCommandTemplate(RerunModel):
    argv: list[RerunTemplateArg] = Field(min_length=1, max_length=256)
    cwd_relative: str = "."
    # RunCommand 已支持 config；详细重跑 lineage 单独保存在 rerun_seed。
    source: Literal["config"] = "config"
    risk_level: Literal["low", "medium", "high"] = "high"
    reason: str = Field(min_length=1, max_length=1000)
    parent_command_sha256: str = Field(pattern=SHA256)
    template_hash: str = Field(pattern=SHA256)

    @field_validator("cwd_relative")
    @classmethod
    def validate_cwd_relative(cls, value: str) -> str:
        if not value or value.startswith("/"):
            raise ValueError("cwd_relative 必须是非空相对路径")
        parts = value.replace("\\", "/").split("/")
        if any(part in {"", ".."} for part in parts):
            raise ValueError("cwd_relative 不能包含空段或 ..")
        return value


class RerunSourceIdentity(RerunModel):
    parent_job_id: str = Field(min_length=1, max_length=200)
    parent_run_id: str = Field(min_length=1, max_length=300)
    parent_workspace_manifest_id: str = Field(min_length=1, max_length=200)
    parent_workspace_manifest_hash: str = Field(pattern=SHA256)
    parent_workspace_generation: int = Field(ge=0)
    parent_run_manifest_artifact_id: str = Field(min_length=1, max_length=300)
    parent_run_manifest_sha256: str = Field(pattern=SHA256)


class RerunProposalCreateRequest(RerunModel):
    parent_job_id: str = Field(min_length=1, max_length=200)
    expected_parent_job_version: int = Field(ge=0)
    expected_parent_run_manifest_sha256: str = Field(pattern=SHA256)
    edits: list[RerunArgumentEdit] = Field(min_length=1, max_length=16)
    experiment_goal: str | None = Field(default=None, max_length=1000)
    execution_profile_id: str | None = Field(default=None, max_length=200)
    comparison_id: str | None = Field(default=None, max_length=200)
    expected_comparison_hash: str | None = Field(default=None, pattern=SHA256)

    @model_validator(mode="after")
    def validate_comparison_binding(self) -> "RerunProposalCreateRequest":
        if (self.comparison_id is None) != (
            self.expected_comparison_hash is None
        ):
            raise ValueError(
                "comparison_id 和 expected_comparison_hash 必须同时提供"
            )
        options = [item.option for item in self.edits]
        if len(options) != len(set(options)):
            raise ValueError("同一 option 不能重复编辑")
        return self


class RerunProposal(RerunModel):
    proposal_version: Literal["phase39-v1"] = "phase39-v1"
    proposal_id: str = Field(pattern=PROPOSAL_ID)
    proposal_hash: str = Field(pattern=SHA256)
    source: RerunSourceIdentity
    comparison_id: str | None = None
    comparison_hash: str | None = Field(default=None, pattern=SHA256)
    edits: list[RerunArgumentEdit]
    command_template: RerunCommandTemplate
    experiment_goal: str
    execution_profile_id: str
    execution_policy_hash: str = Field(pattern=SHA256)
    execution_backend: Literal["local", "conda", "oci"]
    created_at: str
    expires_at: str


RerunProposalStatus = Literal[
    "pending",
    "submitting",
    "submitted",
    "cancelled",
    "expired",
]


class RerunProposalRecord(RerunModel):
    proposal: RerunProposal
    status: RerunProposalStatus
    version: int = Field(ge=0)
    child_job_id: str | None = None
    submit_idempotency_key: str | None = None
    last_error: str | None = None
    updated_at: str


class RerunProposalSubmitRequest(RerunModel):
    expected_proposal_hash: str = Field(pattern=SHA256)
    expected_version: int = Field(ge=0)


class RerunProposalCancelRequest(RerunModel):
    expected_proposal_hash: str = Field(pattern=SHA256)
    expected_version: int = Field(ge=0)
    reason: str = Field(default="user cancelled", min_length=1, max_length=500)


class DerivedRunInput(RerunModel):
    """持久化到子 JobRequest 的最小不可变派生契约。"""

    proposal_id: str = Field(pattern=PROPOSAL_ID)
    proposal_hash: str = Field(pattern=SHA256)
    source: RerunSourceIdentity
    command_template: RerunCommandTemplate


class RerunProposalMutationResponse(RerunModel):
    proposal: RerunProposalRecord
    replayed: bool


class RerunSubmissionResponse(RerunModel):
    proposal: RerunProposalRecord
    child_job_id: str
    job_created: bool
