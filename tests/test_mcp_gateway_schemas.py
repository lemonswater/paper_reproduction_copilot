from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.mcp_gateway.schemas import McpSearchInput
from tests.mcp_gateway_helpers import make_policy


def test_policy_has_one_enabled_static_alias() -> None:
    policy = make_policy()
    selected = policy.enabled_binding("search_external_paper_evidence")
    assert selected is not None
    profile, binding = selected
    assert profile.server_id == "mcpserver_scholar_local"
    assert binding.remote_tool_name == "search_paper_evidence"


@pytest.mark.parametrize("query", ["", " ", "a", chr(0), chr(10)])
def test_search_input_rejects_empty_short_or_control_query(query: str) -> None:
    with pytest.raises(ValidationError):
        McpSearchInput(query=query, limit=2)


def test_search_input_does_not_accept_endpoint_or_tool_name() -> None:
    with pytest.raises(ValidationError):
        McpSearchInput.model_validate({"query": "PSTNet", "limit": 2, "endpoint": "http://127.0.0.1:9999/mcp", "tool_name": "delete_library_item"})
