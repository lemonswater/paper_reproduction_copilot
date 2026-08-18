from __future__ import annotations

import pytest

from app.mcp_export.errors import McpExportRateLimited
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter


def test_rate_limiter_uses_sliding_window() -> None:
    now = [100.0]
    limiter = InMemoryMcpExportRateLimiter(
        max_calls_per_minute=2,
        clock=lambda: now[0],
    )

    limiter.acquire("actor-a")
    limiter.acquire("actor-a")
    with pytest.raises(McpExportRateLimited):
        limiter.acquire("actor-a")

    now[0] = 161.0
    limiter.acquire("actor-a")
