from __future__ import annotations

from types import SimpleNamespace

import pytest

try:
    from app.mcp_gateway.client import SdkMcpClient
    from app.mcp_gateway.errors import McpSchemaDrift
    from app.mcp_gateway.identity import schema_sha256
    from tests.mcp_gateway_helpers import make_binding, make_profile

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _MCP_AVAILABLE,
    reason="mcp SDK not installed (requires Python 3.10+)",
)


def test_verify_pin_rejects_changed_input_schema() -> None:
    client = SdkMcpClient(
        total_timeout_seconds=5,
        max_tools=64,
        max_schema_bytes=20000,
        max_result_bytes=20000,
    )
    binding = make_binding()
    observed = SimpleNamespace(
        input_schema_sha256=schema_sha256(
            {"type": "object", "additionalProperties": True}
        ),
        output_schema_sha256=binding.expected_output_schema_sha256,
    )

    with pytest.raises(McpSchemaDrift):
        client._verify_pin(binding=binding, observed=observed)


def test_observe_does_not_select_dangerous_tool_by_annotation() -> None:
    client = SdkMcpClient(
        total_timeout_seconds=5,
        max_tools=64,
        max_schema_bytes=20000,
        max_result_bytes=20000,
    )
    binding = make_binding()
    profile = make_profile()
    safe = SimpleNamespace(
        name="search_paper_evidence",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        annotations={"readOnlyHint": False},
    )
    dangerous = SimpleNamespace(
        name="delete_library_item",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        annotations={"readOnlyHint": True},
    )

    observed = client._observe_tool(
        profile=profile,
        binding=binding,
        protocol_version="2026-07-28",
        tools=[safe, dangerous],
    )
    assert observed.remote_tool_name == "search_paper_evidence"
