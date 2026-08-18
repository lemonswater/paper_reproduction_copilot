from __future__ import annotations

from pathlib import Path

from app.mcp_contracts.baseline import (
    build_candidate,
    promote_candidate,
)
from app.mcp_contracts.schemas import McpClientProfile
from app.mcp_contracts.snapshot import observe_in_memory
from app.mcp_export.server import build_mcp_export_server
from tests.mcp_export_helpers import build_test_service

MODERN = McpClientProfile(
    profile_id="in-memory-modern",
    transport="in_memory",
    mode="auto",
)
LEGACY = McpClientProfile(
    profile_id="in-memory-legacy",
    transport="in_memory",
    mode="legacy",
)


async def observe_test_surfaces(tmp_path: Path):
    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)
    return [
        await observe_in_memory(server, profile=MODERN),
        await observe_in_memory(server, profile=LEGACY),
    ]


def baseline_from_observations(
    *,
    tmp_path: Path,
    observations: list,
):
    candidate = build_candidate(observations)
    return promote_candidate(
        candidate=candidate,
        baseline_path=tmp_path / "mcp_baseline.json",
        expected_surface_sha256=candidate.surface_sha256,
        reviewed_by="pytest",
        reason="deterministic test baseline",
        replace=False,
        expected_current_baseline_sha256=None,
    )
