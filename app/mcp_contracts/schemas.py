from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


SHA256_PATTERN = r"^[0-9a-f]{64}$"
PROFILE_ID_PATTERN = r"^[a-z][a-z0-9_-]{2,63}$"

McpTransport = Literal["in_memory", "streamable_http"]
McpConnectMode = Literal["auto", "legacy"]
McpEvalMode = Literal["offline", "release"]


class McpContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McpClientProfile(McpContractModel):
    """不含凭证的 Client 运行模板。"""

    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    transport: McpTransport
    mode: McpConnectMode
    enabled: bool = True
    required_for_release: bool = True
    endpoint: str | None = Field(default=None, max_length=500)
    secret_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_transport_fields(self) -> "McpClientProfile":
        if self.transport == "in_memory":
            if self.endpoint is not None or self.secret_name is not None:
                raise ValueError(
                    "in_memory Profile 不能携带 endpoint 或 secret_name"
                )
        elif self.endpoint is None or self.secret_name is None:
            raise ValueError(
                "streamable_http Profile 必须声明 endpoint 和 secret_name"
            )
        return self


class McpToolSurface(McpContractModel):
    name: str = Field(min_length=1, max_length=128)
    description_sha256: str = Field(pattern=SHA256_PATTERN)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] = Field(default_factory=dict)
    contract_sha256: str = Field(pattern=SHA256_PATTERN)


class McpResourceTemplateSurface(McpContractModel):
    uri_template: str = Field(min_length=1, max_length=500)
    name: str = Field(min_length=1, max_length=200)
    mime_type: str | None = Field(default=None, max_length=200)
    description_sha256: str = Field(pattern=SHA256_PATTERN)
    contract_sha256: str = Field(pattern=SHA256_PATTERN)


class McpSurfaceSnapshot(McpContractModel):
    """与 SDK patch version 无关的公开业务 Surface。"""

    schema_version: Literal["phase55-v1"] = "phase55-v1"
    server_name: str = Field(min_length=1, max_length=200)
    server_version: str = Field(min_length=1, max_length=100)
    capability_names: list[str] = Field(default_factory=list)
    tools: list[McpToolSurface] = Field(default_factory=list)
    resource_templates: list[McpResourceTemplateSurface] = Field(
        default_factory=list
    )
    static_resource_uris: list[str] = Field(default_factory=list)
    prompt_names: list[str] = Field(default_factory=list)
    surface_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_deterministic_order(self) -> "McpSurfaceSnapshot":
        if [item.name for item in self.tools] != sorted(
            item.name for item in self.tools
        ):
            raise ValueError("tools 必须按 name 排序")
        if [item.uri_template for item in self.resource_templates] != sorted(
            item.uri_template for item in self.resource_templates
        ):
            raise ValueError("resource_templates 必须按 URI 排序")
        if self.static_resource_uris != sorted(self.static_resource_uris):
            raise ValueError("static_resource_uris 必须排序")
        if self.prompt_names != sorted(self.prompt_names):
            raise ValueError("prompt_names 必须排序")
        return self


class McpRuntimeFingerprint(McpContractModel):
    """记录环境身份，但不参与 Surface Hash。"""

    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    transport: McpTransport
    connect_mode: McpConnectMode
    python_version: str = Field(min_length=1, max_length=50)
    mcp_sdk_version: str = Field(min_length=1, max_length=50)
    mcp_sdk_major: int = Field(ge=1)
    pydantic_version: str = Field(min_length=1, max_length=50)
    protocol_version: str = Field(min_length=1, max_length=50)


class McpSurfaceObservation(McpContractModel):
    profile: McpClientProfile
    runtime: McpRuntimeFingerprint
    surface: McpSurfaceSnapshot


class McpContractCandidate(McpContractModel):
    candidate_id: str = Field(pattern=r"^mcpcandidate_[0-9a-f]{16}$")
    generated_at: str
    profile_ids: list[str] = Field(min_length=1)
    observations: list[McpSurfaceObservation] = Field(min_length=1)
    consistent_surface: bool
    surface_sha256: str = Field(pattern=SHA256_PATTERN)
    candidate_sha256: str = Field(pattern=SHA256_PATTERN)


class McpContractBaseline(McpContractModel):
    schema_version: Literal["phase55-v1"] = "phase55-v1"
    baseline_id: str = Field(pattern=r"^mcpbaseline_[0-9a-f]{16}$")
    accepted_at: str
    reviewed_by: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=500)
    accepted_surface_sha256: str = Field(pattern=SHA256_PATTERN)
    server_name: str = Field(min_length=1, max_length=200)
    server_version: str = Field(min_length=1, max_length=100)
    required_tool_names: list[str] = Field(min_length=1)
    required_resource_templates: list[str] = Field(min_length=1)
    forbidden_name_fragments: list[str] = Field(default_factory=list)
    require_output_schema: bool = True
    allow_static_resources: bool = False
    allow_prompts: bool = False
    allowed_sdk_majors: list[int] = Field(default_factory=lambda: [2])
    allowed_protocol_versions: list[str] = Field(min_length=1)
    required_profile_ids: list[str] = Field(min_length=1)
    baseline_sha256: str = Field(pattern=SHA256_PATTERN)


class McpContractFinding(McpContractModel):
    code: str = Field(min_length=1, max_length=100)
    severity: Literal["error", "warning"]
    summary: str = Field(min_length=1, max_length=500)


class McpProfileEvalResult(McpContractModel):
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    status: Literal["passed", "failed", "skipped"]
    protocol_version: str | None = Field(default=None, max_length=50)
    surface_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    findings: list[McpContractFinding] = Field(default_factory=list)


class McpContractEvalReport(McpContractModel):
    eval_id: str = Field(pattern=r"^mcpeval_[0-9a-f]{16}$")
    mode: McpEvalMode
    generated_at: str
    baseline_sha256: str = Field(pattern=SHA256_PATTERN)
    passed: bool
    profile_results: list[McpProfileEvalResult] = Field(min_length=1)
    report_sha256: str = Field(pattern=SHA256_PATTERN)


class McpStackComponent(McpContractModel):
    name: Literal[
        "sdk",
        "contracts",
        "gateway",
        "export",
        "runtime",
    ]
    status: Literal["ready", "degraded", "not_ready", "disabled"]
    issues: list[str] = Field(default_factory=list)


class McpStackReadinessReport(McpContractModel):
    schema_version: Literal["phase55-v1"] = "phase55-v1"
    status: Literal["ready", "degraded", "not_ready", "disabled"]
    generated_at: str
    components: list[McpStackComponent]
