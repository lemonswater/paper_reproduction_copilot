#!/usr/bin/env python3
"""Phase 53 MCP Gateway 批量创建脚本"""
from pathlib import Path

def main():
    root = Path("/data/tianshaoqi24/agent/paper_reproduction_copilot")
    
    print("开始创建 Phase 53 MCP Gateway 文件...")
    
    # 1. 创建 app/mcp_gateway 目录
    mcp_dir = root / "app" / "mcp_gateway"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ 创建目录: {mcp_dir}")
    
    # 2. 创建 __init__.py
    (mcp_dir / "__init__.py").write_text('"""Phase 53 read-only MCP interoperability gateway。"""\n')
    print("✓ 创建 __init__.py")
    
    # 3. 创建 errors.py
    errors_py = '''from __future__ import annotations


class McpGatewayError(RuntimeError):
    """MCP Gateway 稳定错误基类。"""

    code = "MCP_GATEWAY_ERROR"
    retryable = False


class McpPolicyError(McpGatewayError):
    code = "MCP_POLICY_INVALID"


class McpEndpointRejected(McpGatewayError):
    code = "MCP_ENDPOINT_REJECTED"


class McpServerUnavailable(McpGatewayError):
    code = "MCP_SERVER_UNAVAILABLE"
    retryable = True


class McpProtocolRejected(McpGatewayError):
    code = "MCP_PROTOCOL_REJECTED"


class McpToolNotAllowed(McpGatewayError):
    code = "MCP_TOOL_NOT_ALLOWED"


class McpSchemaDrift(McpGatewayError):
    code = "MCP_SCHEMA_DRIFT"


class McpRemoteToolFailed(McpGatewayError):
    code = "MCP_REMOTE_TOOL_FAILED"
    retryable = True


class McpStructuredOutputInvalid(McpGatewayError):
    code = "MCP_STRUCTURED_OUTPUT_INVALID"


class McpResultBudgetExceeded(McpGatewayError):
    code = "MCP_RESULT_BUDGET_EXCEEDED"


class McpEvidenceIntegrityError(McpGatewayError):
    code = "MCP_EVIDENCE_INTEGRITY_ERROR"
'''
    (mcp_dir / "errors.py").write_text(errors_py)
    print("✓ 创建 errors.py")
    
    # 4. 创建 schemas.py 的一部分(由于文件较大,分多次写入)
    schemas_part1 = '''from __future__ import annotations

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
'''
    (mcp_dir / "schemas.py").write_text(schemas_part1)
    print("✓ 创建 schemas.py (part 1)")
    
    print("第一阶段完成! 基础目录结构和核心错误定义已创建。")

if __name__ == "__main__":
    main()