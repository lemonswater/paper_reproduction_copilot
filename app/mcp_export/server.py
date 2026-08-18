from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Any, NoReturn
from uuid import uuid4

from pydantic import Field

from app.config import settings
from app.mcp_export.call_executor import (
    McpExportCallExecutor,
    McpExportServerContext,
    build_mcp_export_lifespan,
)
from app.mcp_export.errors import McpExportError
from app.mcp_export.schemas import (
    McpExportArtifactPage,
    McpExportEvidencePack,
    McpExportFinalReport,
    McpExportJobStatus,
)
from app.mcp_export.service import ReadOnlyMcpExportService
from app.observability.ports import TelemetryPort
from app.observability.runtime import build_telemetry_runtime


def _request_id(ctx) -> str:
    raw = getattr(ctx, "request_id", None)
    normalized = str(raw).strip() if raw is not None else ""
    return normalized[:200] or f"mcp_{uuid4().hex[:24]}"


def _resource_request_id(kind: str) -> str:
    return f"mcp_resource_{kind}_{uuid4().hex[:16]}"


def _raise_public_error(exc: BaseException) -> NoReturn:
    """只把稳定 code 和公开消息交给 MCP Client。"""

    if isinstance(exc, McpExportError):
        raise RuntimeError(
            f"{exc.code}: {exc.public_message}"
        ) from None
    raise RuntimeError(
        "MCP_EXPORT_INTERNAL: MCP Export internal error"
    ) from None


async def _invoke(
    ctx,
    *,
    metric_operation: str,
    metric_job_id: str,
    metric_request_id: str,
    function: Callable[..., Any],
    function_kwargs: dict[str, object],
    fallback_calls: "McpExportCallExecutor | None" = None,
):
    """把观测字段与业务函数参数分开，避免同名关键字冲突。"""

    calls: McpExportCallExecutor | None = None
    try:
        runtime: McpExportServerContext = (
            ctx.request_context.lifespan_context
        )
        calls = runtime.calls
    except Exception:
        calls = fallback_calls
    if calls is None:
        raise RuntimeError(
            "MCP_EXPORT_INTERNAL: MCP Export internal error"
        )
    return await calls.run(
        operation=metric_operation,
        request_id=metric_request_id,
        job_id=metric_job_id,
        function=function,
        function_kwargs=function_kwargs,
    )


def build_mcp_export_server(
    service: ReadOnlyMcpExportService,
    *,
    telemetry: TelemetryPort | None = None,
):
    # 动态 import 保证 MCP_EXPORT_ENABLED=false 时普通 CLI/API 不依赖 SDK。
    from mcp.server import MCPServer
    from mcp.server.mcpserver import Context
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response

    # from __future__ import annotations 会把 Context 注解保存为字符串。
    # SDK 注册 Tool 时会在模块 globals 中解析它。
    globals()["Context"] = Context

    selected_telemetry = (
        telemetry
        if telemetry is not None
        else build_telemetry_runtime().telemetry
    )
    # 资源 handler 在 SDK 2.0.0 in-memory transport 下无法从
    # ctx.request_context.lifespan_context 获取 executor，
    # 因此在闭包中创建一个共享实例。
    _shared_calls = McpExportCallExecutor(
        workers=settings.mcp_export_handler_workers,
        queue_capacity=settings.mcp_export_handler_queue,
        timeout_seconds=(
            settings.mcp_export_handler_timeout_seconds
        ),
        telemetry=selected_telemetry,
    )
    lifespan = build_mcp_export_lifespan(
        workers=settings.mcp_export_handler_workers,
        queue_capacity=settings.mcp_export_handler_queue,
        timeout_seconds=(
            settings.mcp_export_handler_timeout_seconds
        ),
        telemetry=selected_telemetry,
    )
    mcp = MCPServer(
        "Paper Reproduction Copilot Read-only Export",
        version="phase54-v1",
        lifespan=lifespan,
    )

    @mcp.tool()
    async def get_reproduction_status(
        job_id: Annotated[
            str,
            Field(
                description=(
                    "Server-generated reproduction Job ID: "
                    "job_ followed by 32 lowercase hex characters"
                ),
                pattern=r"^job_[0-9a-f]{32}$",
            ),
        ],
        ctx: Context[McpExportServerContext],
    ) -> McpExportJobStatus:
        """Read a bounded public status snapshot for one known Job."""

        request_id = _request_id(ctx)
        try:
            return await _invoke(
                ctx,
                metric_operation="get_reproduction_status",
                metric_job_id=job_id,
                metric_request_id=request_id,
                function=service.get_status,
                function_kwargs={
                    "job_id": job_id,
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.tool()
    async def list_reproduction_artifacts(
        job_id: Annotated[
            str,
            Field(pattern=r"^job_[0-9a-f]{32}$"),
        ],
        ctx: Context[McpExportServerContext],
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
    ) -> McpExportArtifactPage:
        """List bounded public Artifact metadata without paths."""

        request_id = _request_id(ctx)
        try:
            return await _invoke(
                ctx,
                metric_operation="list_reproduction_artifacts",
                metric_job_id=job_id,
                metric_request_id=request_id,
                function=service.list_artifacts,
                function_kwargs={
                    "job_id": job_id,
                    "limit": limit,
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.tool()
    async def read_reproduction_final_report(
        job_id: Annotated[
            str,
            Field(pattern=r"^job_[0-9a-f]{32}$"),
        ],
        ctx: Context[McpExportServerContext],
    ) -> McpExportFinalReport:
        """Read the server-selected, integrity-checked final report."""

        request_id = _request_id(ctx)
        try:
            return await _invoke(
                ctx,
                metric_operation="read_reproduction_final_report",
                metric_job_id=job_id,
                metric_request_id=request_id,
                function=service.read_final_report,
                function_kwargs={
                    "job_id": job_id,
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.tool()
    async def search_reproduction_evidence(
        job_id: Annotated[
            str,
            Field(pattern=r"^job_[0-9a-f]{32}$"),
        ],
        query: Annotated[
            str,
            Field(
                min_length=1,
                max_length=500,
                description=(
                    "Question used only to rank local Job, Event, "
                    "Artifact and Log evidence"
                ),
            ),
        ],
        ctx: Context[McpExportServerContext],
        limit: Annotated[int, Field(ge=1, le=6)] = 5,
    ) -> McpExportEvidencePack:
        """Search bounded local evidence and return citations."""

        request_id = _request_id(ctx)
        try:
            return await _invoke(
                ctx,
                metric_operation="search_reproduction_evidence",
                metric_job_id=job_id,
                metric_request_id=request_id,
                function=service.search_evidence,
                function_kwargs={
                    "job_id": job_id,
                    "query": query,
                    "limit": limit,
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.resource(
        "repro://jobs/{job_id}/status",
        mime_type="application/json",
    )
    async def job_status_resource(
        job_id: str,
        ctx: Context[McpExportServerContext],
    ) -> str:
        """Public status Resource for one known Job."""

        request_id = _resource_request_id("status")
        try:
            result = await _invoke(
                ctx,
                metric_operation="resource_job_status",
                metric_job_id=job_id,
                metric_request_id=request_id,
                function=service.get_status,
                function_kwargs={
                    "job_id": job_id,
                    "request_id": request_id,
                    "operation": "resource_job_status",
                },
                fallback_calls=_shared_calls,
            )
            return json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.resource(
        "repro://jobs/{job_id}/final-report",
        mime_type="application/json",
    )
    async def final_report_resource(
        job_id: str,
        ctx: Context[McpExportServerContext],
    ) -> str:
        """Integrity-bound JSON projection of one final report."""

        request_id = _resource_request_id("report")
        try:
            result = await _invoke(
                ctx,
                metric_operation="resource_final_report",
                metric_job_id=job_id,
                metric_request_id=request_id,
                function=service.read_final_report,
                function_kwargs={
                    "job_id": job_id,
                    "request_id": request_id,
                    "operation": "resource_final_report",
                },
                fallback_calls=_shared_calls,
            )
            return json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Request) -> Response:
        return JSONResponse(
            {
                "status": "ok",
                "service": "paper-reproduction-mcp-export",
                "version": "phase54-v1",
            }
        )

    return mcp
