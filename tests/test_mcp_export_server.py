from __future__ import annotations

import mcp
import pytest

from tests.mcp_export_helpers import JOB_ID, build_test_service


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_server_lists_exactly_four_read_only_tools(tmp_path) -> None:
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp.Client(
        server,
        raise_exceptions=True,
        read_timeout_seconds=3,
    ) as client:
        listed = await client.list_tools()

    names = {item.name for item in listed.tools}
    assert names == {
        "get_reproduction_status",
        "list_reproduction_artifacts",
        "read_reproduction_final_report",
        "search_reproduction_evidence",
    }
    assert not names.intersection(
        {
            "run_command",
            "submit_decision",
            "approve_action",
            "apply_patch",
            "cancel_job",
        }
    )


async def test_status_tool_returns_structured_content(tmp_path) -> None:
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp.Client(
        server,
        raise_exceptions=True,
        read_timeout_seconds=3,
    ) as client:
        result = await client.call_tool(
            "get_reproduction_status",
            {"job_id": JOB_ID},
            read_timeout_seconds=3,
        )

    assert result.is_error is not True
    assert result.structured_content["job_id"] == JOB_ID
    assert "run_dir" not in result.structured_content


async def test_tool_schema_has_no_path_or_authority_fields(tmp_path) -> None:
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp.Client(
        server,
        raise_exceptions=True,
        read_timeout_seconds=3,
    ) as client:
        listed = await client.list_tools()

    serialized = str(
        [item.input_schema for item in listed.tools]
    ).lower()
    for forbidden in [
        "path",
        "endpoint",
        "token",
        "capability",
        "actor",
        "tool_name",
        "ctx",
    ]:
        assert forbidden not in serialized


async def test_resource_templates_are_fixed(tmp_path) -> None:
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp.Client(
        server,
        raise_exceptions=True,
        read_timeout_seconds=3,
    ) as client:
        listed = await client.list_resource_templates()

    uris = {str(item.uri_template) for item in listed.resource_templates}
    assert uris == {
        "repro://jobs/{job_id}/status",
        "repro://jobs/{job_id}/final-report",
    }


@pytest.mark.parametrize(
    ("profile_id", "mode"),
    [
        ("in-memory-modern", "auto"),
        ("in-memory-legacy", "legacy"),
    ],
)
async def test_export_surface_supports_approved_client_modes(
    tmp_path,
    profile_id: str,
    mode: str,
) -> None:
    from app.mcp_contracts.schemas import McpClientProfile
    from app.mcp_contracts.snapshot import observe_in_memory
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)
    observation = await observe_in_memory(
        server,
        profile=McpClientProfile(
            profile_id=profile_id,
            transport="in_memory",
            mode=mode,
        ),
    )

    assert observation.surface.surface_sha256
    assert observation.runtime.mcp_sdk_major == 2
    assert len(observation.surface.tools) == 4


@pytest.mark.parametrize(
    "mode",
    ["auto", "legacy"],
)
async def test_status_tool_invokes_in_approved_client_modes(
    tmp_path,
    mode: str,
) -> None:
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp.Client(
        server,
        mode=mode,
        raise_exceptions=True,
        read_timeout_seconds=3,
    ) as client:
        # 先读取目录，让 Client 缓存 Tool Output Schema。
        await client.list_tools()
        result = await client.call_tool(
            "get_reproduction_status",
            {"job_id": JOB_ID},
            read_timeout_seconds=3,
        )

    assert result.is_error is not True
    assert result.structured_content is not None
    assert result.structured_content["job_id"] == JOB_ID
