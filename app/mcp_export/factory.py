from __future__ import annotations

from dataclasses import dataclass

from app.artifact_delivery.service import ArtifactDeliveryService
from app.observability.ports import TelemetryPort
from app.observability.runtime import build_telemetry_runtime
from app.chat.context import ChatContextBuilder
from app.config import settings
from app.interaction.service import InteractionService
from app.job_runtime.factory import build_job_store
from app.job_runtime.service import JobService
from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.errors import McpExportDisabled
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter
from app.mcp_export.schemas import McpExportDoctorReport
from app.mcp_export.service import ReadOnlyMcpExportService
from app.secrets.errors import SecretNotFoundError
from app.secrets.factory import build_secret_service
from app.secrets.schemas import SecretUse
from app.storage.factory import build_artifact_storage
from app.tool_calling.evidence_tools import (
    ChatEvidenceToolBindings,
    build_chat_evidence_tool_registry,
)
from app.workspace.snapshot import WorkspaceSnapshotter


TOOL_NAMES = [
    "get_reproduction_status",
    "list_reproduction_artifacts",
    "read_reproduction_final_report",
    "search_reproduction_evidence",
]

RESOURCE_TEMPLATES = [
    "repro://jobs/{job_id}/status",
    "repro://jobs/{job_id}/final-report",
]


@dataclass(frozen=True)
class McpExportRuntime:
    service: ReadOnlyMcpExportService
    audit_repository: SqliteMcpExportAuditRepository
    telemetry: TelemetryPort


def _build_artifact_delivery(storage) -> ArtifactDeliveryService:
    return ArtifactDeliveryService(
        catalog=storage.catalog,
        preview_max_bytes=settings.artifact_preview_max_bytes,
        stream_chunk_bytes=settings.artifact_stream_chunk_bytes,
        export_allowed_root=settings.job_export_allowed_root,
        export_staging_root=settings.job_export_staging_root,
        export_max_artifacts=settings.job_export_max_artifacts,
        export_max_uncompressed_bytes=(
            settings.job_export_max_uncompressed_bytes
        ),
        export_max_archive_bytes=settings.job_export_max_archive_bytes,
        export_staging_ttl_seconds=(
            settings.job_export_staging_ttl_seconds
        ),
    )


def build_mcp_export_runtime(
    *,
    telemetry: TelemetryPort | None = None,
) -> McpExportRuntime:
    if not settings.mcp_export_enabled:
        raise McpExportDisabled("MCP Export is disabled")

    selected_telemetry = (
        telemetry
        if telemetry is not None
        else build_telemetry_runtime().telemetry
    )

    storage = build_artifact_storage()
    job_service = JobService(
        build_job_store(),
        workspace_snapshotter=WorkspaceSnapshotter(
            blob_store=storage.selected_store
        ),
    )
    interaction = InteractionService(job_service)
    delivery = _build_artifact_delivery(storage)

    # 第一版只构造本地 Job/Artifact/Event/Log Context，不注入 Research、
    # MCP Gateway、Knowledge 或 Project Fact Retriever。
    context_builder = ChatContextBuilder(
        interaction=interaction,
        artifact_catalog=storage.catalog,
        artifacts_to_open=settings.chat_artifacts_to_open,
        source_limit=settings.chat_source_limit,
        artifact_max_bytes=settings.chat_artifact_max_bytes,
        total_context_chars=settings.chat_total_context_chars,
        log_max_bytes=settings.chat_log_max_bytes,
    )
    evidence_registry = build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(
            context_builder=context_builder,
            # 显式 None，防止 Phase 53 MCP Gateway 被递归导出。
            mcp_gateway=None,
        )
    )

    audit = SqliteMcpExportAuditRepository(
        settings.mcp_export_audit_db_path
    )
    audit.initialize()
    limiter = InMemoryMcpExportRateLimiter(
        max_calls_per_minute=(
            settings.mcp_export_max_calls_per_minute
        )
    )
    service = ReadOnlyMcpExportService(
        interaction=interaction,
        artifact_delivery=delivery,
        evidence_registry=evidence_registry,
        audit_repository=audit,
        rate_limiter=limiter,
        redactor=build_secret_service().build_redactor(
            actor="runtime:mcp-export-redactor"
        ),
        max_artifacts=settings.mcp_export_max_artifacts,
        max_report_chars=settings.mcp_export_max_report_chars,
    )
    return McpExportRuntime(
        service=service,
        audit_repository=audit,
        telemetry=selected_telemetry,
    )


def resolve_mcp_export_token() -> str:
    """仅在启动 MCP Export 进程时解析明文 Token。"""

    material = build_secret_service().resolve_current(
        name=settings.mcp_export_token_secret_name,
        use=SecretUse.MCP_EXPORT_AUTH,
        actor="runtime:mcp-export-auth",
    )
    return material.reveal()


def inspect_mcp_export() -> McpExportDoctorReport:
    issues: list[str] = []
    token_available = False
    audit_ready = False

    if settings.mcp_export_host != "127.0.0.1":
        issues.append("mcp_export_host_not_loopback")

    try:
        # Doctor 只验证 Secret 存在、状态正常且允许用于 MCP Export，
        # 不调用 reveal()，避免把明文 Token 留在局部变量中。
        build_secret_service().resolve_current(
            name=settings.mcp_export_token_secret_name,
            use=SecretUse.MCP_EXPORT_AUTH,
            actor="doctor:mcp-export-auth",
        )
        token_available = True
    except SecretNotFoundError:
        issues.append("mcp_export_token_missing")
    except Exception as exc:
        issues.append(f"mcp_export_token_invalid:{type(exc).__name__}")

    try:
        repository = SqliteMcpExportAuditRepository(
            settings.mcp_export_audit_db_path
        )
        repository.initialize()
        repository.ping()
        audit_ready = True
    except Exception as exc:
        issues.append(f"mcp_export_audit_invalid:{type(exc).__name__}")

    return McpExportDoctorReport(
        enabled=settings.mcp_export_enabled,
        ready=(
            settings.mcp_export_enabled
            and token_available
            and audit_ready
            and not issues
        ),
        host=settings.mcp_export_host,
        port=settings.mcp_export_port,
        token_available=token_available,
        audit_ready=audit_ready,
        tool_names=list(TOOL_NAMES),
        resource_templates=list(RESOURCE_TEMPLATES),
        issues=issues,
    )
