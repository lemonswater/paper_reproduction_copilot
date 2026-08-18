from __future__ import annotations

import sys
from importlib import metadata
from typing import Any, cast

from app.mcp_contracts.errors import (
    McpContractDependencyMissing,
    McpSurfaceObservationFailed,
)
from app.mcp_contracts.identity import (
    resource_template_surface,
    surface_snapshot,
    tool_surface,
)
from app.mcp_contracts.schemas import (
    McpClientProfile,
    McpRuntimeFingerprint,
    McpSurfaceObservation,
)
from app.mcp_export.server import build_mcp_export_server
from app.mcp_export.service import ReadOnlyMcpExportService


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError as exc:
        raise McpContractDependencyMissing(
            f"required distribution is missing: {name}"
        ) from exc


def _major(version: str) -> int:
    raw = version.split(".", 1)[0]
    if not raw.isdigit():
        raise McpSurfaceObservationFailed("SDK version is invalid")
    return int(raw)


def _dump(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return dict(value)
    raise McpSurfaceObservationFailed("MCP metadata is not serializable")


def _capability_names(value: Any) -> list[str]:
    payload = _dump(value)
    return sorted(
        name
        for name, item in payload.items()
        if item not in (None, False, {}, [])
    )


async def _list_all_tools(client) -> list[Any]:
    items: list[Any] = []
    cursor = None
    while True:
        page = await client.list_tools(cursor=cursor)
        items.extend(page.tools)
        cursor = page.next_cursor
        if cursor is None:
            return items


async def _list_all_templates(client) -> list[Any]:
    items: list[Any] = []
    cursor = None
    while True:
        page = await client.list_resource_templates(cursor=cursor)
        items.extend(page.resource_templates)
        cursor = page.next_cursor
        if cursor is None:
            return items


async def _list_all_resources(client) -> list[Any]:
    items: list[Any] = []
    cursor = None
    while True:
        page = await client.list_resources(cursor=cursor)
        items.extend(page.resources)
        cursor = page.next_cursor
        if cursor is None:
            return items


async def _list_all_prompts(client) -> list[Any]:
    items: list[Any] = []
    cursor = None
    while True:
        page = await client.list_prompts(cursor=cursor)
        items.extend(page.prompts)
        cursor = page.next_cursor
        if cursor is None:
            return items


async def observe_connected_client(
    client,
    *,
    profile: McpClientProfile,
) -> McpSurfaceObservation:
    """观察 Client 真正看到的目录，不调用任何业务 Tool。"""

    try:
        tools = await _list_all_tools(client)
        templates = await _list_all_templates(client)

        capabilities = client.server_capabilities
        static_resources = (
            await _list_all_resources(client)
            if getattr(capabilities, "resources", None) is not None
            else []
        )
        prompts = (
            await _list_all_prompts(client)
            if getattr(capabilities, "prompts", None) is not None
            else []
        )

        server_info = client.server_info
        if server_info is None:
            raise McpSurfaceObservationFailed(
                "MCP Server did not report server_info"
            )

        tool_items = sorted(
            [
                tool_surface(
                    name=item.name,
                    description=item.description or "",
                    input_schema=dict(item.input_schema),
                    output_schema=(
                        dict(item.output_schema)
                        if item.output_schema is not None
                        else None
                    ),
                    annotations=_dump(item.annotations),
                )
                for item in tools
            ],
            key=lambda item: item.name,
        )
        template_items = sorted(
            [
                resource_template_surface(
                    uri_template=str(item.uri_template),
                    name=item.name,
                    mime_type=item.mime_type,
                    description=item.description or "",
                )
                for item in templates
            ],
            key=lambda item: item.uri_template,
        )

        surface = surface_snapshot(
            schema_version="phase55-v1",
            server_name=server_info.name,
            server_version=server_info.version,
            capability_names=_capability_names(capabilities),
            tools=tool_items,
            resource_templates=template_items,
            static_resource_uris=sorted(
                str(item.uri) for item in static_resources
            ),
            prompt_names=sorted(item.name for item in prompts),
        )
        sdk_version = _distribution_version("mcp")
        runtime = McpRuntimeFingerprint(
            profile_id=profile.profile_id,
            transport=profile.transport,
            connect_mode=profile.mode,
            python_version=(
                f"{sys.version_info.major}."
                f"{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
            mcp_sdk_version=sdk_version,
            mcp_sdk_major=_major(sdk_version),
            pydantic_version=_distribution_version("pydantic"),
            protocol_version=str(client.protocol_version),
        )
        return McpSurfaceObservation(
            profile=profile,
            runtime=runtime,
            surface=surface,
        )
    except McpSurfaceObservationFailed:
        raise
    except Exception as exc:
        # 不把远端正文或 Header 写进稳定错误。
        raise McpSurfaceObservationFailed(
            f"surface observation failed: {type(exc).__name__}"
        ) from exc


async def observe_in_memory(
    server,
    *,
    profile: McpClientProfile,
    timeout_seconds: float = 5.0,
) -> McpSurfaceObservation:
    if profile.transport != "in_memory":
        raise McpSurfaceObservationFailed("profile transport mismatch")

    try:
        from mcp import Client
    except ImportError as exc:
        raise McpContractDependencyMissing(
            "install project dev/mcp extras"
        ) from exc

    async with Client(
        server,
        mode=profile.mode,
        raise_exceptions=True,
        read_timeout_seconds=timeout_seconds,
    ) as client:
        return await observe_connected_client(client, profile=profile)


async def observe_streamable_http(
    *,
    profile: McpClientProfile,
    token: str,
    timeout_seconds: float,
) -> McpSurfaceObservation:
    """真实 loopback HTTP 观察；Token 只存在于短生命周期 AsyncClient。"""

    if profile.transport != "streamable_http" or profile.endpoint is None:
        raise McpSurfaceObservationFailed("profile transport mismatch")

    try:
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
    except ImportError as exc:
        raise McpContractDependencyMissing(
            "install project dev/mcp extras"
        ) from exc

    # 不继承环境 Proxy，不跟随 Redirect，避免 loopback Policy 被协议层绕过。
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx2.Timeout(timeout_seconds),
        follow_redirects=False,
        trust_env=False,
    ) as http_client:
        transport = streamable_http_client(
            profile.endpoint,
            http_client=http_client,
        )
        async with Client(
            transport,
            mode=profile.mode,
            read_timeout_seconds=timeout_seconds,
        ) as client:
            return await observe_connected_client(
                client,
                profile=profile,
            )


class CatalogOnlyService:
    """只用于 in-memory tools/list；任何业务调用都确定性失败。"""

    @staticmethod
    def _deny():
        raise RuntimeError("catalog-only service cannot execute tools")

    def get_status(self, **_kwargs):
        return self._deny()

    def list_artifacts(self, **_kwargs):
        return self._deny()

    def read_final_report(self, **_kwargs):
        return self._deny()

    def search_evidence(self, **_kwargs):
        return self._deny()


def build_catalog_only_server():
    """不连接 Job Store、Artifact、Secret 或 Phase 53 Gateway。"""

    service = cast(
        ReadOnlyMcpExportService,
        CatalogOnlyService(),
    )
    return build_mcp_export_server(service)
