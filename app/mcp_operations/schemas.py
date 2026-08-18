from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.mcp_contracts.schemas import McpRuntimeFingerprint


SHA256_PATTERN = r"^[0-9a-f]{64}$"
PROFILE_ID_PATTERN = r"^[a-z][a-z0-9_-]{2,63}$"

McpOperationKind = Literal["tool", "resource"]
McpOperationStatus = Literal[
    "succeeded",
    "failed",
    "timeout",
    "busy",
    "protocol_error",
    "schema_error",
    "transport_error",
]


class McpOperationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McpRuntimePolicy(McpOperationModel):
    schema_version: Literal["phase56-v1"] = "phase56-v1"
    offline_profile_ids: list[str] = Field(min_length=1)
    release_profile_ids: list[str] = Field(min_length=1)
    required_operation_names: list[str] = Field(min_length=1)
    samples_per_operation: int = Field(ge=1, le=20)
    minimum_success_rate: float = Field(ge=0.0, le=1.0)
    maximum_p95_ms: float = Field(gt=0, le=60_000)
    request_timeout_seconds: float = Field(gt=0, le=60)
    maximum_relative_p95_regression: float = Field(ge=0, le=5)
    maximum_absolute_p95_regression_ms: float = Field(ge=0, le=60_000)
    allowed_sdk_majors: list[int] = Field(min_length=1)
    allowed_protocol_versions: list[str] = Field(min_length=1)
    policy_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_deterministic_lists(self) -> McpRuntimePolicy:
        for name, values in (
            ("offline_profile_ids", self.offline_profile_ids),
            ("release_profile_ids", self.release_profile_ids),
            ("required_operation_names", self.required_operation_names),
            ("allowed_sdk_majors", self.allowed_sdk_majors),
            ("allowed_protocol_versions", self.allowed_protocol_versions),
        ):
            if values != sorted(set(values)):
                raise ValueError(f"{name} 必须去重并排序")
        return self


class McpInvocationSample(McpOperationModel):
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    operation: str = Field(min_length=1, max_length=100)
    kind: McpOperationKind
    sample_index: int = Field(ge=0)
    status: McpOperationStatus
    duration_ms: float = Field(ge=0)
    output_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    error_code: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_result_identity(self) -> McpInvocationSample:
        if self.status == "succeeded":
            if self.output_sha256 is None or self.error_code is not None:
                raise ValueError("成功样本必须只有 output_sha256")
        elif self.output_sha256 is not None or self.error_code is None:
            raise ValueError("失败样本必须只有稳定 error_code")
        return self


class McpOperationSummary(McpOperationModel):
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    operation: str = Field(min_length=1, max_length=100)
    kind: McpOperationKind
    sample_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    p95_ms: float = Field(ge=0)
    passed: bool
    finding_codes: list[str] = Field(default_factory=list)


class McpRuntimeProfileResult(McpOperationModel):
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    runtime: McpRuntimeFingerprint | None = None
    surface_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    operation_summaries: list[McpOperationSummary]
    passed: bool
    finding_codes: list[str] = Field(default_factory=list)


class McpRuntimeReport(McpOperationModel):
    schema_version: Literal["phase56-v1"] = "phase56-v1"
    report_id: str = Field(pattern=r"^mcpruntime_[0-9a-f]{16}$")
    mode: Literal["offline", "release"]
    generated_at: str
    policy_sha256: str = Field(pattern=SHA256_PATTERN)
    baseline_sha256: str = Field(pattern=SHA256_PATTERN)
    passed: bool
    # Coverage 缺失时仍要能生成失败报告，而不是报告层再次崩溃。
    profiles: list[McpRuntimeProfileResult] = Field(
        default_factory=list
    )
    samples: list[McpInvocationSample] = Field(default_factory=list)
    finding_codes: list[str] = Field(default_factory=list)
    report_sha256: str = Field(pattern=SHA256_PATTERN)


class McpUpgradeOperationComparison(McpOperationModel):
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    operation: str = Field(min_length=1, max_length=100)
    before_p95_ms: float = Field(ge=0)
    after_p95_ms: float = Field(ge=0)
    absolute_change_ms: float
    relative_change: float
    passed: bool
    finding_codes: list[str] = Field(default_factory=list)


class McpUpgradeComparison(McpOperationModel):
    schema_version: Literal["phase56-v1"] = "phase56-v1"
    comparison_id: str = Field(pattern=r"^mcpupgrade_[0-9a-f]{16}$")
    generated_at: str
    before_report_sha256: str = Field(pattern=SHA256_PATTERN)
    after_report_sha256: str = Field(pattern=SHA256_PATTERN)
    accepted_surface_sha256: str = Field(pattern=SHA256_PATTERN)
    passed: bool
    operation_comparisons: list[McpUpgradeOperationComparison]
    finding_codes: list[str] = Field(default_factory=list)
    comparison_sha256: str = Field(pattern=SHA256_PATTERN)
