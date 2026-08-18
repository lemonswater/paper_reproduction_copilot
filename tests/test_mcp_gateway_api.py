from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.mcp_gateway_routes import router
from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import McpSearchInput
from tests.mcp_gateway_helpers import FakeMcpClient, make_policy


def _client(
    repository: SqliteMcpEvidenceRepository | None,
    *,
    api_token: str | None = None,
) -> TestClient:
    app = FastAPI()
    app.state.api_token = api_token
    app.state.mcp_evidence_repository = repository
    app.include_router(router)
    return TestClient(app)


def _seed_pack(repository: SqliteMcpEvidenceRepository):
    gateway = ReadOnlyMcpEvidenceGateway(
        policy=make_policy(),
        client=FakeMcpClient(),
        repository=repository,
    )
    return gateway.search(
        job_id="job-1",
        request_id="api-seed-1",
        payload=McpSearchInput(query="PSTNet", limit=1),
    )


def test_disabled_mcp_evidence_returns_404() -> None:
    response = _client(None).get("/v1/jobs/job-1/mcp-evidence")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MCP_GATEWAY_DISABLED"


def test_list_and_get_mcp_pack(tmp_path) -> None:
    repository = SqliteMcpEvidenceRepository(tmp_path / "mcp.sqlite")
    repository.initialize()
    pack = _seed_pack(repository)
    client = _client(repository)

    listed = client.get("/v1/jobs/job-1/mcp-evidence")
    fetched = client.get(
        f"/v1/jobs/job-1/mcp-evidence/{pack.pack_id}"
    )

    assert listed.status_code == 200
    assert listed.json()[0]["pack_id"] == pack.pack_id
    assert fetched.status_code == 200
    assert fetched.json()["pack_sha256"] == pack.pack_sha256


def test_mcp_pack_cannot_be_read_through_another_job(tmp_path) -> None:
    repository = SqliteMcpEvidenceRepository(tmp_path / "mcp.sqlite")
    repository.initialize()
    pack = _seed_pack(repository)
    response = _client(repository).get(
        f"/v1/jobs/job-2/mcp-evidence/{pack.pack_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MCP_EVIDENCE_NOT_FOUND"


def test_mcp_evidence_api_requires_configured_token(tmp_path) -> None:
    repository = SqliteMcpEvidenceRepository(tmp_path / "mcp.sqlite")
    repository.initialize()
    response = _client(
        repository,
        api_token="test-token",
    ).get("/v1/jobs/job-1/mcp-evidence")
    assert response.status_code == 401


def test_mcp_api_has_no_generic_call_endpoint(tmp_path) -> None:
    repository = SqliteMcpEvidenceRepository(tmp_path / "mcp.sqlite")
    repository.initialize()
    response = _client(repository).post(
        "/v1/jobs/job-1/mcp-evidence",
        json={
            "server_id": "mcpserver_scholar_local",
            "tool_name": "delete_library_item",
            "arguments": {"item_id": "danger"},
        },
    )
    assert response.status_code == 405
