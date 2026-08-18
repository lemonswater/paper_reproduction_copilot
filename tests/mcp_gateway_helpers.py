from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.mcp_gateway.identity import (
    compute_pack_hash,
    schema_sha256,
    sha256_value,
    stable_id,
)
from app.mcp_gateway.schemas import (
    McpEvidencePack,
    McpGatewayPolicy,
    McpObservedTool,
    McpRawCallResult,
    McpServerProfile,
    McpToolBinding,
)


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 2, "maxLength": 400},
        "limit": {"type": "integer", "minimum": 1, "maximum": 6},
    },
    "required": ["query", "limit"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "source_uri": {"type": "string"},
                    "excerpt": {"type": "string"},
                    "locator": {"type": "string"},
                },
                "required": ["title", "source_uri", "excerpt", "locator"],
                "additionalProperties": False,
            },
        },
        "truncated": {"type": "boolean"},
    },
    "required": ["items", "truncated"],
    "additionalProperties": False,
}


def make_binding() -> McpToolBinding:
    return McpToolBinding(
        binding_id="mcpbind_scholar_search_v1",
        provider_alias="search_external_paper_evidence",
        internal_tool_name="mcp.search_external_paper_evidence",
        remote_tool_name="search_paper_evidence",
        expected_input_schema_sha256=schema_sha256(INPUT_SCHEMA),
        expected_output_schema_sha256=schema_sha256(OUTPUT_SCHEMA),
    )


def make_profile(*, enabled: bool = True) -> McpServerProfile:
    return McpServerProfile(
        server_id="mcpserver_scholar_local",
        endpoint="http://127.0.0.1:8765/mcp",
        enabled=enabled,
        bindings=[make_binding()],
    )


def make_policy(*, enabled: bool = True) -> McpGatewayPolicy:
    return McpGatewayPolicy(
        policy_version="test-v1",
        servers=[make_profile(enabled=enabled)],
    )


def observed_tool() -> McpObservedTool:
    return McpObservedTool(
        server_id="mcpserver_scholar_local",
        protocol_version="2026-07-28",
        remote_tool_name="search_paper_evidence",
        input_schema=INPUT_SCHEMA,
        output_schema=OUTPUT_SCHEMA,
        input_schema_sha256=schema_sha256(INPUT_SCHEMA),
        output_schema_sha256=schema_sha256(OUTPUT_SCHEMA),
    )


def remote_payload() -> dict[str, Any]:
    return {
        "items": [
            {
                "title": "PSTNet",
                "source_uri": "https://example.org/pstnet?utm_source=test",
                "excerpt": "Point spatio-temporal convolution evidence.",
                "locator": "fixture:paper:1",
            }
        ],
        "truncated": False,
    }


@dataclass
class FakeMcpClient:
    payload: dict[str, Any] = field(default_factory=remote_payload)
    calls: list[dict[str, Any]] = field(default_factory=list)
    inspected: McpObservedTool = field(default_factory=observed_tool)

    def inspect_tool(self, *, profile, binding) -> McpObservedTool:
        self.calls.append({"kind": "inspect", "server_id": profile.server_id, "remote_tool_name": binding.remote_tool_name})
        return self.inspected

    def call_pinned_tool(self, *, profile, binding, arguments) -> McpRawCallResult:
        self.calls.append({"kind": "call", "server_id": profile.server_id, "remote_tool_name": binding.remote_tool_name, "arguments": arguments})
        return McpRawCallResult(observed_tool=self.inspected, structured_content=self.payload, result_sha256=sha256_value(self.payload))
