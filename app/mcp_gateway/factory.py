from __future__ import annotations

from app.config import settings
from app.mcp_gateway.errors import McpGatewayError
from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.policy import (
    load_mcp_gateway_policy,
    policy_sha256,
)
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import McpInspectReport


def build_mcp_repository() -> SqliteMcpEvidenceRepository:
    repository = SqliteMcpEvidenceRepository(settings.mcp_gateway_db_path)
    repository.initialize()
    return repository


def build_mcp_client():
    from app.mcp_gateway.client import SdkMcpClient
    return SdkMcpClient(
        total_timeout_seconds=settings.mcp_gateway_total_timeout_seconds,
        max_tools=settings.mcp_gateway_max_tools,
        max_schema_bytes=settings.mcp_gateway_max_schema_bytes,
        max_result_bytes=settings.mcp_gateway_max_result_bytes,
    )


def build_read_only_mcp_gateway() -> ReadOnlyMcpEvidenceGateway:
    if not settings.mcp_gateway_enabled:
        raise RuntimeError("MCP Gateway is disabled")
    policy = load_mcp_gateway_policy(settings.mcp_gateway_policy_path, allowed_root=settings.allowed_root)
    return ReadOnlyMcpEvidenceGateway(policy=policy, client=build_mcp_client(), repository=build_mcp_repository())


def inspect_mcp_gateway(*, connect: bool) -> McpInspectReport:
    if not settings.mcp_gateway_enabled:
        return McpInspectReport(enabled=False, ready=False, issues=["mcp_gateway_disabled"])
    try:
        policy = load_mcp_gateway_policy(settings.mcp_gateway_policy_path, allowed_root=settings.allowed_root)
        selected = policy.enabled_binding(ReadOnlyMcpEvidenceGateway.ALIAS)
        if selected is None:
            return McpInspectReport(enabled=True, ready=False, policy_version=policy.policy_version, policy_sha256=policy_sha256(policy), issues=["mcp_search_binding_not_enabled"])
        profile, binding = selected
        issues: list[str] = []
        if connect:
            observed = build_mcp_client().inspect_tool(profile=profile, binding=binding)
            if observed.input_schema_sha256 != binding.expected_input_schema_sha256:
                issues.append("mcp_input_schema_drift")
            if observed.output_schema_sha256 != binding.expected_output_schema_sha256:
                issues.append("mcp_output_schema_drift")
        return McpInspectReport(enabled=True, ready=not issues, policy_version=policy.policy_version, policy_sha256=policy_sha256(policy), server_ids=[profile.server_id], bindings=[binding.binding_id], issues=issues)
    except Exception as exc:
        code = exc.code if isinstance(exc, McpGatewayError) else type(exc).__name__
        return McpInspectReport(enabled=True, ready=False, issues=[f"mcp_gateway_invalid:{code}"])
