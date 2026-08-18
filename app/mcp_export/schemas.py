from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


JOB_ID_PATTERN = r"^job_[0-9a-f]{32}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class McpExportModel(BaseModel):
    """所有 MCP Export 对象都拒绝未知字段，防止协议静默漂移。"""

    model_config = ConfigDict(extra="forbid")


class McpExportJobStatus(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    run_id: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    waiting_for_user: bool
    allowed_operation_kinds: list[str] = Field(
        default_factory=list,
        max_length=8,
    )
    final_status: str | None = Field(
        default=None,
        max_length=100,
    )
    stage_error_count: int | None = Field(default=None, ge=0)
    output_file_count: int | None = Field(default=None, ge=0)
    has_error: bool
    error_code: str | None = Field(default=None, max_length=100)
    created_at: str
    updated_at: str
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)


class McpExportArtifact(McpExportModel):
    artifact_id: str = Field(min_length=1, max_length=200)
    run_id: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=255)
    layer: str = Field(min_length=1, max_length=100)
    media_type: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=0)
    producer_node: str = Field(min_length=1, max_length=200)
    created_at: str
    preview_supported: bool

    @field_validator("display_name")
    @classmethod
    def reject_path_like_name(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("display_name 只能是 basename")
        return value


class McpExportArtifactPage(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    run_id: str = Field(min_length=1, max_length=200)
    items: list[McpExportArtifact] = Field(
        default_factory=list,
        max_length=100,
    )
    returned_count: int = Field(ge=0)
    truncated: bool
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_count(self) -> "McpExportArtifactPage":
        if self.returned_count != len(self.items):
            raise ValueError("returned_count 与 items 数量不一致")
        return self


class McpExportFinalReport(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    run_id: str = Field(min_length=1, max_length=200)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_sha256: str = Field(pattern=SHA256_PATTERN)
    media_type: Literal["text/markdown", "text/plain"]
    total_size_bytes: int = Field(ge=0)
    returned_chars: int = Field(ge=0)
    truncated: bool
    content: str = Field(max_length=100000)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_length(self) -> "McpExportFinalReport":
        if self.returned_chars != len(self.content):
            raise ValueError("returned_chars 与 content 长度不一致")
        return self


class McpExportCitation(McpExportModel):
    citation_id: str = Field(min_length=1, max_length=300)
    source_type: Literal["job", "event", "artifact", "log"]
    label: str = Field(min_length=1, max_length=300)
    artifact_id: str | None = Field(default=None, max_length=200)
    artifact_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    event_id: int | None = Field(default=None, ge=0)


class McpExportEvidenceItem(McpExportModel):
    citation: McpExportCitation
    excerpt: str = Field(min_length=1, max_length=4000)
    excerpt_sha256: str = Field(pattern=SHA256_PATTERN)


class McpExportEvidencePack(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    query_sha256: str = Field(pattern=SHA256_PATTERN)
    items: list[McpExportEvidenceItem] = Field(
        default_factory=list,
        max_length=6,
    )
    truncated: bool
    pack_sha256: str = Field(pattern=SHA256_PATTERN)


class McpExportAuditRecord(McpExportModel):
    call_id: str = Field(pattern=r"^mcpexportcall_[0-9a-f]{24}$")
    request_id: str = Field(min_length=1, max_length=200)
    actor_fingerprint: str = Field(pattern=SHA256_PATTERN)
    operation: Literal[
        "get_reproduction_status",
        "list_reproduction_artifacts",
        "read_reproduction_final_report",
        "search_reproduction_evidence",
        "resource_job_status",
        "resource_final_report",
    ]
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    status: Literal["succeeded", "failed"]
    input_sha256: str = Field(pattern=SHA256_PATTERN)
    output_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    error_code: str | None = Field(default=None, max_length=100)
    started_at: str
    finished_at: str
    duration_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_result_shape(self) -> "McpExportAuditRecord":
        if self.status == "succeeded":
            if self.output_sha256 is None or self.error_code is not None:
                raise ValueError("成功 Audit 必须只有 output_sha256")
        elif self.error_code is None or self.output_sha256 is not None:
            raise ValueError("失败 Audit 必须只有 error_code")
        return self


class McpExportDoctorReport(McpExportModel):
    enabled: bool
    ready: bool
    host: str
    port: int = Field(ge=1, le=65535)
    token_available: bool
    audit_ready: bool
    tool_names: list[str] = Field(default_factory=list)
    resource_templates: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
