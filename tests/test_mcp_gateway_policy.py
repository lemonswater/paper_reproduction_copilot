from __future__ import annotations

import pytest

from app.mcp_gateway.errors import McpEndpointRejected, McpPolicyError
from app.mcp_gateway.policy import validate_loopback_endpoint


@pytest.mark.parametrize("endpoint", ["http://localhost:8765/mcp", "https://127.0.0.1:8765/mcp", "http://127.0.0.1:8765/other", "http://127.0.0.1/mcp", "http://127.0.0.1:80/mcp", "http://example.com:8765/mcp", "http://user:pass@127.0.0.1:8765/mcp", "http://127.0.0.1:8765/mcp?q=1", "http://127.0.0.1:8765/mcp#frag", "ftp://127.0.0.1:8765/mcp"])
def test_reject_invalid_endpoints(endpoint: str) -> None:
    with pytest.raises((McpEndpointRejected, McpPolicyError)):
        validate_loopback_endpoint(endpoint)


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:8765/mcp", "http://[::1]:8765/mcp"])
def test_accept_valid_loopback_endpoints(endpoint: str) -> None:
    validate_loopback_endpoint(endpoint)
