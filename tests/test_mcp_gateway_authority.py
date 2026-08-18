from __future__ import annotations

import tempfile
from pathlib import Path

from app.mcp_gateway.errors import McpGatewayError
from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import McpSearchInput
from tests.mcp_gateway_helpers import FakeMcpClient, make_policy


def test_mcp_gateway_only_returns_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()
        gateway = ReadOnlyMcpEvidenceGateway(policy=make_policy(), client=FakeMcpClient(), repository=repo)
        pack = gateway.search(job_id="job_auth", request_id="req_001", payload=McpSearchInput(query="PSTNet", limit=3))
        assert hasattr(pack, "items")
        assert not hasattr(pack, "decision")
        assert not hasattr(pack, "executable_action")
        assert not hasattr(pack, "patch")


def test_mcp_gateway_does_not_modify_graph_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()
        gateway = ReadOnlyMcpEvidenceGateway(policy=make_policy(), client=FakeMcpClient(), repository=repo)
        pack = gateway.search(job_id="job_state", request_id="req_002", payload=McpSearchInput(query="PSTNet", limit=3))
        assert pack.job_id == "job_state"
        assert pack.server_id == "mcpserver_scholar_local"
