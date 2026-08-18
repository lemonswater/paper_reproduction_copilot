from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SHA256_PATTERN = r"^[0-9a-f]{64}$"


class McpGatewayModel(BaseModel):
    """所有 Policy、持久化和跨层对象都拒绝未知字段。"""

    model_config = ConfigDict(extra="forbid")


class McpToolBinding(McpGatewayModel):
    """本地 Alias 与一个远端 Tool 的静态绑定。"""

    binding_id: str = Field(
        pattern=r"^mcpbind_[a-z0-9][a-z0-9_-]{2,63}$"
    )
    provider_alias: Literal["search_external_paper_evidence"]
    internal_tool_name: Literal["mcp.search_external_paper_evidence"]
    remote_tool_name: str = Field(
        pattern=r"^[A-Za-z0-9_.-]{1,128}$"
    )
    expected_input_schema_sha256: str = Field(
        pattern=SHA256_PATTERN
    )
    expected_output_schema_sha256: str = Field(
        pattern=SHA256_PATTERN
    )


class McpServerProfile(McpGatewayModel):
    """本地声明的 Server 身份；远端 server_info 不能替代它。"""

    server_id: str = Field(
        pattern=r"^mcpserver_[a-z0-9][a-z0-9_-]{2,63}$"
    )
    transport: Literal["streamable_http"] = "streamable_http"
    endpoint: str = Field(min_length=1, max_length=500)
    allowed_protocol_versions: list[
        Literal["2026-07-28"]
    ] = Field(default_factory=lambda: ["2026-07-28"])
    connect_timeout_seconds: float = Field(default=3.0, gt=0, le=10)
    read_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    enabled: bool = False
    bindings: list[McpToolBinding] = Field(
        min_length=1,
        max_length=4,
    )

    @model_validator(mode="after")
    def validate_unique_bindings(self) -> "McpServerProfile":
        binding_ids = [item.binding_id for item in self.bindings]
        aliases = [item.provider_alias for item in self.bindings]
        remote_names = [item.remote_tool_name for item in self.bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("MCP binding_id 不能重复")
        if len(aliases) != len(set(aliases)):
            raise ValueError("同一 Server 的 Provider Alias 不能重复")
        if len(remote_names) != len(set(remote_names)):
            raise ValueError("同一 Server 的 remote tool 不能重复")
        return self


class McpGatewayPolicy(McpGatewayModel):
    schema_version: Literal["phase53-v1"] = "phase53-v1"
    policy_version: str = Field(min_length=1, max_length=100)
    servers: list[McpServerProfile] = Field(
        min_length=1,
        max_length=8,
    )

    @model_validator(mode="after")
    def validate_unique_servers(self) -> "McpGatewayPolicy":
        server_ids = [item.server_id for item in self.servers]
        if len(server_ids) != len(set(server_ids)):
            raise ValueError("MCP server_id 不能重复")

        enabled_aliases = [
            binding.provider_alias
            for server in self.servers
            if server.enabled
            for binding in server.bindings
        ]
        if len(enabled_aliases) != len(set(enabled_aliases)):
            raise ValueError("已启用 MCP Server 的 Provider Alias 不能冲突")
        return self

    def enabled_binding(
        self,
        alias: str,
    ) -> tuple[McpServerProfile, McpToolBinding] | None:
        matches = [
            (server, binding)
            for server in self.servers
            if server.enabled
            for binding in server.bindings
            if binding.provider_alias == alias
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError("MCP Alias 映射不唯一")
        return matches[0]


class McpSearchInput(McpGatewayModel):
    """模型可见的参数；不包含 Server、URL、Tool Name 或 Job ID。"""

    query: str = Field(min_length=2, max_length=400)
    limit: int = Field(default=5, ge=1, le=6)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in value
        ):
            raise ValueError("MCP query 不能包含控制字符")
        normalized = " ".join(value.strip().split())
        if len(normalized) < 2:
            raise ValueError("MCP query 太短")
        return normalized


class RemotePaperEvidenceItem(McpGatewayModel):
    """第一版唯一允许的远端业务输出项。"""

    title: str = Field(min_length=1, max_length=500)
    source_uri: str = Field(min_length=1, max_length=2048)
    excerpt: str = Field(min_length=1, max_length=4000)
    locator: str = Field(default="remote search result", max_length=500)


class RemotePaperSearchResult(McpGatewayModel):
    items: list[RemotePaperEvidenceItem] = Field(
        default_factory=list,
        max_length=6,
    )
    truncated: bool = False


class McpObservedTool(McpGatewayModel):
    """一次连接内观察到的远端 Tool 契约快照。"""

    server_id: str
    protocol_version: str
    remote_tool_name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    input_schema_sha256: str = Field(pattern=SHA256_PATTERN)
    output_schema_sha256: str = Field(pattern=SHA256_PATTERN)


class McpRawCallResult(McpGatewayModel):
    """SDK Adapter 返回给领域 Gateway 的最小结果。"""

    observed_tool: McpObservedTool
    structured_content: dict[str, Any]
    result_sha256: str = Field(pattern=SHA256_PATTERN)


class McpEvidenceItem(McpGatewayModel):
    item_id: str = Field(pattern=r"^mcpitem_[0-9a-f]{24}$")
    title: str = Field(min_length=1, max_length=500)
    source_uri: str = Field(min_length=1, max_length=2048)
    excerpt: str = Field(min_length=1, max_length=4000)
    locator: str = Field(min_length=1, max_length=500)
    item_sha256: str = Field(pattern=SHA256_PATTERN)


class McpEvidencePack(McpGatewayModel):
    pack_id: str = Field(pattern=r"^mcppack_[0-9a-f]{24}$")
    job_id: str = Field(min_length=1, max_length=200)
    server_id: str
    binding_id: str
    profile_sha256: str = Field(pattern=SHA256_PATTERN)
    input_schema_sha256: str = Field(pattern=SHA256_PATTERN)
    output_schema_sha256: str = Field(pattern=SHA256_PATTERN)
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    result_sha256: str = Field(pattern=SHA256_PATTERN)
    created_at: str
    items: list[McpEvidenceItem] = Field(
        default_factory=list,
        max_length=6,
    )
    truncated: bool = False
    pack_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_unique_items(self) -> "McpEvidencePack":
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("MCP Evidence item_id 不能重复")
        return self


McpCallStatus = Literal["succeeded", "failed"]


class McpCallRecord(McpGatewayModel):
    call_id: str = Field(pattern=r"^mcpcall_[0-9a-f]{24}$")
    job_id: str
    server_id: str
    binding_id: str
    profile_sha256: str = Field(pattern=SHA256_PATTERN)
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    result_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    status: McpCallStatus
    error_code: str | None = None
    protocol_version: str | None = None
    started_at: str
    finished_at: str
    duration_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_status_fields(self) -> "McpCallRecord":
        if self.status == "succeeded":
            if self.result_sha256 is None or self.error_code is not None:
                raise ValueError("成功 MCP Call 的 result/error 字段不一致")
        elif self.error_code is None:
            raise ValueError("失败 MCP Call 必须有稳定 error_code")
        return self


class McpInspectReport(McpGatewayModel):
    enabled: bool
    ready: bool
    policy_version: str | None = None
    policy_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    server_ids: list[str] = Field(default_factory=list)
    bindings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)