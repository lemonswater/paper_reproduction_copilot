from __future__ import annotations

import tempfile
from pathlib import Path

from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import McpSearchInput
from tests.mcp_gateway_helpers import FakeMcpClient, make_policy


def test_search_returns_pack_with_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()
        client = FakeMcpClient()
        gateway = ReadOnlyMcpEvidenceGateway(policy=make_policy(), client=client, repository=repo)
        pack = gateway.search(job_id="job_test", request_id="req_001", payload=McpSearchInput(query="PSTNet", limit=3))
        assert pack.job_id == "job_test"
        assert pack.server_id == "mcpserver_scholar_local"
        assert pack.binding_id == "mcpbind_scholar_search_v1"
        assert len(pack.items) == 1
        assert pack.items[0].title == "PSTNet"
        assert pack.truncated is False
        assert len(client.calls) == 1
        assert client.calls[0]["kind"] == "call"


def test_search_failure_records_call() -> None:
    from app.mcp_gateway.errors import McpRemoteToolFailed
    from app.mcp_gateway.schemas import McpSearchInput

    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()

        class FailingClient(FakeMcpClient):
            def call_pinned_tool(self, *, profile, binding, arguments):
                raise McpRemoteToolFailed("remote MCP tool failed")

        gateway = ReadOnlyMcpEvidenceGateway(policy=make_policy(), client=FailingClient(), repository=repo)
        try:
            gateway.search(job_id="job_fail", request_id="req_002", payload=McpSearchInput(query="PSTNet", limit=3))
            assert False, "should have raised"
        except McpRemoteToolFailed:
            pass
        calls = repo.list_calls_for_job(job_id="job_fail")
        assert len(calls) == 1
        assert calls[0].status == "failed"
        assert calls[0].error_code == "MCP_REMOTE_TOOL_FAILED"
