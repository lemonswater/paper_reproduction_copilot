from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.mcp_contracts.schemas import McpClientProfile


def test_in_memory_profile_rejects_endpoint() -> None:
    with pytest.raises(ValidationError):
        McpClientProfile(
            profile_id="in-memory-modern",
            transport="in_memory",
            mode="auto",
            endpoint="http://127.0.0.1:8770/mcp",
        )


def test_http_profile_requires_secret_name() -> None:
    with pytest.raises(ValidationError):
        McpClientProfile(
            profile_id="loopback-http",
            transport="streamable_http",
            mode="auto",
            endpoint="http://127.0.0.1:8770/mcp",
        )


def test_profile_has_no_raw_token_field() -> None:
    fields = set(McpClientProfile.model_fields)
    assert "token" not in fields
    assert "authorization" not in fields
    assert "headers" not in fields
