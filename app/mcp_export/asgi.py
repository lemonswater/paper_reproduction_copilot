from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.mcp_export.auth import LocalBearerAuthMiddleware
from app.mcp_export.factory import (
    McpExportRuntime,
    build_mcp_export_runtime,
    resolve_mcp_export_token,
)
from app.mcp_export.server import build_mcp_export_server


@dataclass(frozen=True)
class McpExportAsgiBundle:
    mcp_server: Any
    app: Any
    runtime: McpExportRuntime


def build_mcp_export_asgi_bundle(
    *,
    runtime: McpExportRuntime | None = None,
    token: str | None = None,
) -> McpExportAsgiBundle:
    selected_runtime = runtime or build_mcp_export_runtime()
    selected_token = token or resolve_mcp_export_token()
    server = build_mcp_export_server(
        selected_runtime.service,
        telemetry=selected_runtime.telemetry,
    )

    # 不 Mount 到另一个应用，因此 SDK 自带 lifespan 可以正常启动
    # session_manager；默认 transport security 继续保护 localhost Host。
    inner = server.streamable_http_app()
    protected = LocalBearerAuthMiddleware(
        inner,
        expected_token=selected_token,
        public_paths={"/healthz"},
    )
    return McpExportAsgiBundle(
        mcp_server=server,
        app=protected,
        runtime=selected_runtime,
    )
