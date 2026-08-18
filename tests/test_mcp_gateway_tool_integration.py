from __future__ import annotations

import tempfile
from pathlib import Path

from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.tool_adapter import (
    MCP_CAPABILITY,
    MCP_INTERNAL_TOOL_NAME,
    register_mcp_evidence_tool,
)
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ToolInvocationContext
from tests.mcp_gateway_helpers import FakeMcpClient, make_policy


def _registry(tmp_path) -> ToolRegistry:
    repository = SqliteMcpEvidenceRepository(Path(tmp_path) / "mcp.sqlite")
    repository.initialize()
    gateway = ReadOnlyMcpEvidenceGateway(
        policy=make_policy(),
        client=FakeMcpClient(),
        repository=repository,
    )
    registry = ToolRegistry()
    register_mcp_evidence_tool(registry=registry, gateway=gateway)
    return registry


def test_mcp_tool_requires_explicit_capability(tmp_path) -> None:
    registry = _registry(tmp_path)
    result = registry.invoke(
        name=MCP_INTERNAL_TOOL_NAME,
        raw_input={"query": "PSTNet", "limit": 1},
        context=ToolInvocationContext(
            actor="agent:test",
            request_id="request-1",
            caller_kind="agent",
            job_id="job-1",
            granted_capabilities=set(),
        ),
    )
    assert result.failure is not None
    assert result.failure.code == "TOOL_CAPABILITY_DENIED"


def test_mcp_tool_returns_mcp_citation_when_capability_granted(
    tmp_path,
) -> None:
    registry = _registry(tmp_path)
    result = registry.invoke(
        name=MCP_INTERNAL_TOOL_NAME,
        raw_input={"query": "PSTNet", "limit": 1},
        context=ToolInvocationContext(
            actor="agent:test",
            request_id="request-1",
            caller_kind="agent",
            job_id="job-1",
            granted_capabilities={MCP_CAPABILITY},
        ),
    )
    assert result.failure is None
    assert result.output is not None
    citation = result.output["items"][0]["citation"]
    assert citation["source_type"] == "mcp"
    assert citation["mcp_pack_id"].startswith("mcppack_")
