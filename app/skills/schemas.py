from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SkillSideEffectLevel = Literal[
    "read_only",
    "proposal_only",
]


class SkillModel(BaseModel):
    """所有公开 Skill 协议拒绝未知字段，避免 Manifest 静默漂移。"""

    model_config = ConfigDict(extra="forbid")


class SkillToolRequirement(SkillModel):
    name: str = Field(
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
    )
    version: str


class SkillResource(SkillModel):
    relative_path: str = Field(min_length=1, max_length=300)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        raw = value.strip()
        if "\\" in raw:
            raise ValueError("Skill Resource 必须使用 POSIX 相对路径")
        path = PurePosixPath(raw)
        normalized = path.as_posix()
        if (
            not raw
            or path.is_absolute()
            or raw != normalized
            or normalized.startswith(".")
            or ".." in path.parts
            or ":" in path.parts[0]
        ):
            raise ValueError("Skill Resource 必须是安全相对路径")
        return normalized


class SkillManifest(SkillModel):
    manifest_version: Literal["phase48-v1"] = "phase48-v1"
    skill_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,63}$"
    )
    skill_version: str = Field(
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$"
    )
    display_name: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)

    implementation_id: str = Field(
        pattern=r"^builtin\.[a-z][a-z0-9_]*\.v[1-9][0-9]*$"
    )
    input_schema_id: str = Field(
        pattern=r"^[a-z][a-z0-9_.-]{2,100}$"
    )
    output_schema_id: str = Field(
        pattern=r"^[a-z][a-z0-9_.-]{2,100}$"
    )

    required_tools: list[SkillToolRequirement] = Field(
        min_length=1,
        max_length=32,
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        max_length=64,
    )
    side_effect_level: SkillSideEffectLevel

    prompt_or_policy_version: str = Field(
        min_length=1,
        max_length=100,
    )
    eval_suite: str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,100}$"
    )
    feature_flag: str = Field(
        pattern=r"^skill\.[a-z][a-z0-9_]{2,63}$"
    )

    max_tool_calls: int = Field(default=8, ge=1, le=32)
    max_duration_ms: float = Field(default=5000, gt=0, le=120000)
    resources: list[SkillResource] = Field(
        default_factory=list,
        max_length=32,
    )

    @model_validator(mode="after")
    def validate_manifest(self) -> SkillManifest:
        tool_names = [item.name for item in self.required_tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("required_tools 不能重复")
        if len(self.required_capabilities) != len(
            set(self.required_capabilities)
        ):
            raise ValueError("required_capabilities 不能重复")
        resource_paths = [item.relative_path for item in self.resources]
        if len(resource_paths) != len(set(resource_paths)):
            raise ValueError("resources relative_path 不能重复")
        if self.feature_flag != f"skill.{self.skill_id}":
            raise ValueError("feature_flag 必须绑定当前 skill_id")
        return self


class SkillInvocationContext(SkillModel):
    """由可信 Host 生成，不能从 LLM payload 反序列化。"""

    actor: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    job_id: str | None = None
    workspace_root: str
    run_root: str
    granted_capabilities: list[str] = Field(
        default_factory=list,
        max_length=64,
    )


class SkillInvocationRequest(SkillModel):
    skill_id: str
    skill_version: str
    expected_skill_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    input_payload: dict[str, Any]


class SkillToolCallRef(SkillModel):
    call_id: str
    tool_name: str
    tool_version: str
    status: Literal["succeeded", "failed"]
    input_sha256: str
    output_sha256: str | None = None
    error_code: str | None = None


class SkillFailure(SkillModel):
    code: str = Field(pattern=r"^SKILL_[A-Z0-9_]{2,80}$")
    category: Literal["user", "policy", "tool", "skill", "environment"]
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool = False


class SkillInvocationRecord(SkillModel):
    invocation_id: str = Field(
        pattern=r"^skillcall_[0-9a-f]{16}$"
    )
    skill_id: str
    skill_version: str
    skill_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["succeeded", "failed"]
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    failure_code: str | None = None
    tool_calls: list[SkillToolCallRef] = Field(default_factory=list)
    actor: str
    request_id: str
    job_id: str | None = None
    started_at: str
    finished_at: str
    duration_ms: float = Field(ge=0)


class SkillExecutionResult(SkillModel):
    output: dict[str, Any] | None = None
    failure: SkillFailure | None = None
    record: SkillInvocationRecord

    @model_validator(mode="after")
    def validate_shape(self) -> SkillExecutionResult:
        if self.record.status == "succeeded":
            if self.output is None or self.failure is not None:
                raise ValueError("Skill 成功时必须只有 output")
        elif self.failure is None or self.output is not None:
            raise ValueError("Skill 失败时必须只有 failure")
        return self


class SkillCatalogEntry(SkillModel):
    skill_id: str
    skill_version: str
    display_name: str
    summary: str
    side_effect_level: SkillSideEffectLevel
    required_tools: list[str]
    required_capabilities: list[str]
    prompt_or_policy_version: str
    eval_suite: str
    feature_flag: str
    enabled: bool
    skill_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class SkillValidationIssue(SkillModel):
    code: str
    target: str
    message: str


class SkillValidationReport(SkillModel):
    ok: bool
    packages_checked: int = Field(ge=0)
    skills_bound: int = Field(ge=0)
    issues: list[SkillValidationIssue] = Field(default_factory=list)
