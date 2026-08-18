from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.mcp_gateway.errors import McpGatewayError
from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.identity import stable_id
from app.mcp_gateway.schemas import McpEvidencePack, McpSearchInput

if TYPE_CHECKING:
    from app.tool_calling.schemas import EvidenceToolOutput
    from app.tool_contracts.registry import ToolRegistry
    from app.tool_contracts.schemas import ToolFailure


MCP_INTERNAL_TOOL_NAME = "mcp.search_external_paper_evidence"
MCP_PROVIDER_ALIAS = "search_external_paper_evidence"
MCP_CAPABILITY = "mcp.read.external"


class McpEvidenceGatewayPort(Protocol):
    @property
    def authority_fingerprint(self) -> str:
        ...

    def search(self, *, job_id: str, request_id: str, payload: McpSearchInput) -> McpEvidencePack:
        ...


def _pack_to_output(pack: McpEvidencePack) -> "EvidenceToolOutput":
    from app.tool_calling.schemas import EvidenceToolOutput, ToolEvidenceItem

    items: list[ToolEvidenceItem] = []
    for item in pack.items:
        citation_id = stable_id("mcpcit", {"pack_id": pack.pack_id, "pack_sha256": pack.pack_sha256, "item_id": item.item_id, "item_sha256": item.item_sha256})
        from app.chat.schemas import ChatCitation
        citation = ChatCitation(
            citation_id=citation_id,
            source_type="mcp",
            label=item.title,
            locator=item.locator,
            mcp_server_id=pack.server_id,
            mcp_binding_id=pack.binding_id,
            mcp_profile_sha256=pack.profile_sha256,
            mcp_input_schema_sha256=pack.input_schema_sha256,
            mcp_output_schema_sha256=pack.output_schema_sha256,
            mcp_pack_id=pack.pack_id,
            mcp_pack_sha256=pack.pack_sha256,
            mcp_item_id=item.item_id,
            mcp_item_sha256=item.item_sha256,
            mcp_source_uri=item.source_uri,
        )
        items.append(ToolEvidenceItem(
            citation=citation,
            content=(
                f"title: {item.title}\n"
                f"source: {item.source_uri}\n"
                f"locator: {item.locator}\n"
                f"excerpt: {item.excerpt}"
            ),
        ))
    return EvidenceToolOutput(summary="Pinned read-only MCP paper evidence", items=items, truncated=pack.truncated)


def _map_mcp_error(exc: BaseException) -> "ToolFailure | None":
    from app.tool_contracts.schemas import ToolFailure

    if isinstance(exc, McpGatewayError):
        return ToolFailure(code=exc.code, category=("environment" if exc.retryable else "policy"), retryable=exc.retryable, message="Pinned MCP evidence tool did not return usable evidence")
    return None


MCP_DECLARED_ERRORS = [
    {"code": "MCP_GATEWAY_ERROR", "category": "tool", "retryable": False, "summary": "MCP gateway failed safely"},
    {"code": "MCP_POLICY_INVALID", "category": "policy", "retryable": False, "summary": "MCP policy is invalid"},
    {"code": "MCP_ENDPOINT_REJECTED", "category": "policy", "retryable": False, "summary": "MCP endpoint was rejected"},
    {"code": "MCP_SERVER_UNAVAILABLE", "category": "environment", "retryable": True, "summary": "MCP server is unavailable"},
    {"code": "MCP_PROTOCOL_REJECTED", "category": "policy", "retryable": False, "summary": "MCP protocol version changed"},
    {"code": "MCP_TOOL_NOT_ALLOWED", "category": "policy", "retryable": False, "summary": "MCP tool is not pinned"},
    {"code": "MCP_SCHEMA_DRIFT", "category": "policy", "retryable": False, "summary": "MCP schema hash changed"},
    {"code": "MCP_REMOTE_TOOL_FAILED", "category": "environment", "retryable": True, "summary": "Remote MCP tool failed"},
    {"code": "MCP_STRUCTURED_OUTPUT_INVALID", "category": "tool", "retryable": False, "summary": "MCP output is invalid"},
    {"code": "MCP_RESULT_BUDGET_EXCEEDED", "category": "policy", "retryable": False, "summary": "MCP output is too large"},
    {"code": "MCP_EVIDENCE_INTEGRITY_ERROR", "category": "tool", "retryable": False, "summary": "MCP evidence hash failed"},
]


def register_mcp_evidence_tool(*, registry: "ToolRegistry", gateway: McpEvidenceGatewayPort) -> None:
    from app.tool_contracts.schemas import (
        ToolDeterminism, ToolEffect, ToolErrorSpec, ToolExposure,
        ToolInvocationContext, ToolRisk,
    )
    from app.tool_contracts.registry import build_tool_definition
    from app.tool_calling.schemas import EvidenceToolOutput

    declared_errors = [
        ToolErrorSpec(code=e["code"], category=e["category"], retryable=e["retryable"], summary=e["summary"])
        for e in MCP_DECLARED_ERRORS
    ]

    def search_external(payload: McpSearchInput, context: ToolInvocationContext) -> EvidenceToolOutput:
        if context.job_id is None or not context.job_id.strip():
            raise McpGatewayError("MCP Tool missing trusted job scope")
        pack = gateway.search(job_id=context.job_id, request_id=context.request_id, payload=payload)
        return _pack_to_output(pack)

    registry.register(
        build_tool_definition(
            name=MCP_INTERNAL_TOOL_NAME,
            version="phase53-v1",
            summary="Search a pinned local MCP scholarly source and return bounded evidence for the current reproduction Job",
            input_model=McpSearchInput,
            output_model=EvidenceToolOutput,
            handler=search_external,
            error_mapper=_map_mcp_error,
            effects=[ToolEffect.NETWORK_READ],
            required_capabilities=[MCP_CAPABILITY],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.MEDIUM,
            determinism=ToolDeterminism.PROVIDER_DEPENDENT,
            idempotent=True,
            timeout_seconds=30,
            audit_event="tool.mcp.search_external_paper_evidence",
            path_scopes=[],
            declared_errors=declared_errors,
        )
    )
