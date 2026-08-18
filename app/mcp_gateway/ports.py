from __future__ import annotations

from typing import Any, Protocol

from app.mcp_gateway.schemas import (
    McpRawCallResult,
    McpServerProfile,
    McpToolBinding,
    McpObservedTool,
)


class McpClientPort(Protocol):
    """Gateway 只依赖这两个同步方法，测试可使用纯内存 Fake。"""

    def inspect_tool(
        self,
        *,
        profile: McpServerProfile,
        binding: McpToolBinding,
    ) -> McpObservedTool:
        ...

    def call_pinned_tool(
        self,
        *,
        profile: McpServerProfile,
        binding: McpToolBinding,
        arguments: dict[str, Any],
    ) -> McpRawCallResult:
        ...
