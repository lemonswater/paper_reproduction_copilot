from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4
from datetime import datetime, timezone
import time

from fastapi import FastAPI, Request, Response
import json
from pydantic import SecretStr

from app.api.chat_routes import router as chat_router
from app.api.comparison_routes import router as comparison_router
from app.api.errors import (
    install_error_handlers,
)
from app.api.failure_case_routes import (
    router as failure_case_router,
)
from app.api.notification_routes import (
    router as notification_router,
)
from app.api.project_memory_routes import (
    router as project_memory_router,
)
from app.api.resource_routes import router as resource_router
from app.api.routes import router
from app.api.ui_routes import router as ui_router
from app.api.knowledge_routes import (
    router as knowledge_router,
)
from app.api.retention_routes import router as retention_router
from app.api.rerun_routes import router as rerun_router
from app.api.model_routing_routes import (
    router as model_routing_router,
)
from app.api.research_browser_routes import (
    router as research_browser_router,
)
from app.model_routing.gateway import ModelGateway
from app.artifact_delivery.service import (
    ArtifactDeliveryService,
)
from app.chat.context import ChatContextBuilder
from app.chat.service import (
    ChatService,
    build_chat_service,
)
from app.comparison.factory import build_comparison_service
from app.comparison.service import ComparisonService
from app.rerun.factory import build_rerun_service
from app.rerun.service import RerunService
from app.chat.store import SqliteChatRepository
from app.config import settings
from app.failure_memory.factory import (
    build_failure_case_service,
)
from app.failure_memory.service import FailureCaseService
from app.interaction.artifacts import (
    ArtifactCatalog,
)
from app.interaction.service import (
    InteractionService,
)
from app.job_runtime.service import (
    JobService,
)
from app.notifications.factory import (
    build_notification_service,
)
from app.notifications.service import NotificationService
from app.project_memory.factory import (
    build_project_memory_service,
)
from app.project_memory.service import ProjectMemoryService
from app.resources.service import (
    build_resource_service,
)
from app.secrets.service import SecretService
from app.storage.factory import (
    build_artifact_storage,
)
from app.observability.context import bind_telemetry_context
from app.observability.runtime import build_telemetry_runtime
from app.observability.readiness import (
    ReadinessService, ReadinessProbe, build_liveness_probe,
)
from app.observability.json_logging import configure_structured_logging
from app.web import mount_web_ui

if TYPE_CHECKING:
    from app.research_browser.service import ResearchBrowserService


def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: (
        ArtifactCatalog | None
    ) = None,
    artifact_delivery_service: (
        ArtifactDeliveryService | None
    ) = None,
    api_token: str | None = None,
    secret_service: SecretService | None = None,
    service_host: Any | None = None,
    chat_service: ChatService | None = None,
    # 测试可注入内存 ComparisonService，避免写真实 comparisons/。
    comparison_service: ComparisonService | None = None,
    # Phase 39：测试可注入内存 RerunService。
    rerun_service: RerunService | None = None,
    notification_service: NotificationService | None = None,
    failure_case_service: FailureCaseService | None = None,
    project_memory_service: ProjectMemoryService | None = None,
    model_gateway: ModelGateway | None = None,
    research_browser_service: (
        "ResearchBrowserService | None"
    ) = None,
) -> FastAPI:
    """
    App factory 允许测试注入临时 Job DB 和伪 checkpoint reader。
    """

    if settings.structured_logging_enabled:
        configure_structured_logging()

    telemetry_runtime = build_telemetry_runtime()
    telemetry = telemetry_runtime.telemetry

    # 生产入口必须使用 SecretService。显式 api_token 仅用于测试，
    # 此时不要求测试环境预先初始化本地 Vault。
    if secret_service is None and api_token is None:
        from app.secrets.factory import build_secret_service

        secret_service = build_secret_service()

    storage = None
    if job_service is None or artifact_catalog is None:
        storage = build_artifact_storage()

    if job_service is None:
        from app.workspace.snapshot import (
            WorkspaceSnapshotter,
        )

        assert storage is not None
        from app.job_runtime.factory import (
            build_job_store,
        )

        job_service = JobService(
            build_job_store(),
            workspace_snapshotter=WorkspaceSnapshotter(
                blob_store=storage.selected_store
            ),
            telemetry=telemetry,
        )

    selected_job_service = job_service

    app = FastAPI(
        title=(
            "Paper Reproduction Copilot API"
        ),
        version="1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    selected_catalog = (
        artifact_catalog
        if artifact_catalog is not None
        else storage.catalog
    )

    if selected_catalog is None:
        raise RuntimeError(
            "Artifact delivery 需要可用的 ArtifactCatalog"
        )

    selected_delivery_service = (
        artifact_delivery_service
        if artifact_delivery_service is not None
        else ArtifactDeliveryService(
            catalog=selected_catalog,
            preview_max_bytes=(
                settings.artifact_preview_max_bytes
            ),
            stream_chunk_bytes=(
                settings.artifact_stream_chunk_bytes
            ),
            export_allowed_root=(
                settings.job_export_allowed_root
            ),
            export_staging_root=(
                settings.job_export_staging_root
            ),
            export_max_artifacts=(
                settings.job_export_max_artifacts
            ),
            export_max_uncompressed_bytes=(
                settings.job_export_max_uncompressed_bytes
            ),
            export_max_archive_bytes=(
                settings.job_export_max_archive_bytes
            ),
            export_staging_ttl_seconds=(
                settings.job_export_staging_ttl_seconds
            ),
        )
    )

    app.state.artifact_catalog = (
        selected_catalog
    )
    app.state.artifact_delivery_service = (
        selected_delivery_service
    )
    app.state.secret_service = secret_service
    app.state.api_token_secret_name = (
        settings.api_token_secret_name
    )
    app.state.api_token_override = (
        SecretStr(api_token)
        if api_token is not None
        else None
    )

    # Phase 29：Resource 控制面 service（独立 SQLite/Postgres catalog）。
    resource_service = build_resource_service(
        telemetry=telemetry
    )
    app.state.resource_service = resource_service

    # InteractionService 注入 resource_service 用于解析 published Resource。
    app.state.interaction_service = (
        InteractionService(
            selected_job_service,
            resource_service=resource_service,
        )
    )

    # Phase 38 Comparison Service
    selected_comparison_service = (
        comparison_service
        if comparison_service is not None
        else build_comparison_service(
            jobs=selected_job_service.store,
            artifact_catalog=selected_catalog,
        )
    )
    app.state.comparison_service = selected_comparison_service

    # Phase 39 Rerun Service
    selected_rerun_service = (
        rerun_service
        if rerun_service is not None
        else build_rerun_service(
            job_service=selected_job_service,
            artifact_catalog=selected_catalog,
            comparison_service=selected_comparison_service,
        )
    )
    app.state.rerun_service = selected_rerun_service

    # Phase 44 Notification Service
    selected_notification_service = (
        notification_service
        if notification_service is not None
        else build_notification_service(
            jobs=selected_job_service
        )
    )
    app.state.notification_service = (
        selected_notification_service
    )

    # Phase 45 Failure Memory Service
    selected_failure_case_service = (
        failure_case_service
        if failure_case_service is not None
        else build_failure_case_service(
            job_service=selected_job_service,
            artifact_catalog=selected_catalog,
        )
    )
    app.state.failure_case_service = (
        selected_failure_case_service
    )

    # Phase 46 Project Memory Service
    selected_project_memory_service = project_memory_service
    if (
        selected_project_memory_service is None
        and settings.project_memory_enabled
    ):
        chat_repo_for_pm = (
            SqliteChatRepository(settings.chat_db_path)
            if chat_service is None
            else None
        )
        if chat_repo_for_pm is not None:
            chat_repo_for_pm.initialize()
        selected_project_memory_service = build_project_memory_service(
            job_service=selected_job_service,
            chat_repository=(
                chat_repo_for_pm
                if chat_repo_for_pm is not None
                else chat_service.repository  # type: ignore[union-attr]
            ),
        )
    app.state.project_memory_service = (
        selected_project_memory_service
    )

    # Phase 49 Knowledge Base Service (before Chat so retriever is available)
    selected_knowledge_service = None
    if settings.knowledge_base_enabled:
        from app.knowledge_base.factory import (
            build_knowledge_service,
        )

        selected_knowledge_service = build_knowledge_service(
            job_service=selected_job_service,
            artifact_catalog=selected_catalog,
        )
    app.state.knowledge_service = selected_knowledge_service

    # Phase 50 Model Routing Gateway
    if model_gateway is None:
        from app.model_routing.factory import (
            build_model_gateway,
        )

        model_gateway = build_model_gateway()
    app.state.model_gateway = model_gateway

    # Phase 51 Research Browser：关闭时不构造网络组件。
    selected_research_browser_service = (
        research_browser_service
    )
    if (
        selected_research_browser_service is None
        and settings.research_browser_enabled
    ):
        from app.research_browser.factory import (
            build_research_browser_service,
        )

        selected_research_browser_service = (
            build_research_browser_service(
                model_gateway=model_gateway,
                resource_service=resource_service,
                secret_service=secret_service,
            )
        )
    app.state.research_browser_service = (
        selected_research_browser_service
    )

    # Phase 31 Chat Agent
    selected_chat_service = chat_service
    if selected_chat_service is None and settings.chat_enabled:
        if selected_catalog is None:
            raise RuntimeError(
                "CHAT_ENABLED 需要可用的 ArtifactCatalog"
            )
        chat_repository = SqliteChatRepository(
            settings.chat_db_path
        )
        chat_repository.initialize()
        knowledge_retriever = None
        if selected_knowledge_service is not None:
            knowledge_retriever = selected_knowledge_service.retriever
        context_builder = ChatContextBuilder(
            interaction=app.state.interaction_service,
            artifact_catalog=selected_catalog,
            artifacts_to_open=(
                settings.chat_artifacts_to_open
            ),
            source_limit=settings.chat_source_limit,
            artifact_max_bytes=(
                settings.chat_artifact_max_bytes
            ),
            total_context_chars=(
                settings.chat_total_context_chars
            ),
            log_max_bytes=settings.chat_log_max_bytes,
            comparison_reader=selected_comparison_service,
            comparison_limit=settings.comparison_chat_limit,
            comparison_max_chars=settings.comparison_chat_max_chars,
            knowledge_retriever=knowledge_retriever,
            research_reader=(
                selected_research_browser_service.repository
                if selected_research_browser_service is not None
                else None
            ),
        )
        selected_chat_service = build_chat_service(
            repository=chat_repository,
            interaction=app.state.interaction_service,
            context_builder=context_builder,
        )

    app.state.chat_service = selected_chat_service

    def db_check() -> str:
        try:
            selected_job_service.store.ping()
            return "ready"
        except Exception:
            return "not_ready"

    def storage_check() -> str:
        try:
            if storage is not None and hasattr(storage, "ping"):
                storage.ping()
            return "ready"
        except Exception:
            return "degraded"

    def resource_db_check() -> str:
        try:
            resource_service.repository.ping()
            return "ready"
        except Exception:
            return "not_ready"

    probes = [
        ReadinessProbe(
            name="db_readiness",
            is_critical=True,
            check=db_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
        ReadinessProbe(
            name="resource_db_readiness",
            is_critical=True,
            check=resource_db_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
        ReadinessProbe(
            name="storage_readiness",
            is_critical=False,
            check=storage_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
    ]

    if service_host is not None:
        probes.append(
            ReadinessProbe(
                name="embedded_workers",
                is_critical=True,
                check=service_host.readiness,
                timeout_seconds=(
                    settings.readiness_timeout_seconds
                ),
            )
        )

    def _chat_ping(service: ChatService) -> bool:
        try:
            service.ping()
            return True
        except Exception:
            return False

    if selected_chat_service is not None:
        probes.append(
            ReadinessProbe(
                name="chat_db_readiness",
                is_critical=True,
                check=lambda: (
                    "ready"
                    if _chat_ping(selected_chat_service)
                    else "not_ready"
                ),
                timeout_seconds=(
                    settings.readiness_timeout_seconds
                ),
            )
        )

        if settings.chat_tool_calling_enabled:
            def _tool_calling_check() -> str:
                try:
                    from app.tool_calling.factory import (
                        doctor_chat_tool_calling,
                    )

                    report = doctor_chat_tool_calling(
                        context_builder=context_builder,
                    )
                    return "ready" if report.ready else "not_ready"
                except Exception:
                    return "not_ready"

            probes.append(
                ReadinessProbe(
                    name="chat_tool_calling",
                    is_critical=False,
                    check=_tool_calling_check,
                    timeout_seconds=(
                        settings.readiness_timeout_seconds
                    ),
                )
            )

    probes.append(
        ReadinessProbe(
            name="comparison_repository_readiness",
            is_critical=False,
            check=lambda: (
                selected_comparison_service.repository.ping() or "ready"
            ),
            timeout_seconds=settings.readiness_timeout_seconds,
        )
    )

    probes.append(
        ReadinessProbe(
            name="rerun_repository_readiness",
            is_critical=True,
            check=lambda: (
                "ready"
                if selected_rerun_service.repository.ping()
                else "not_ready"
            ),
            timeout_seconds=settings.readiness_timeout_seconds,
        )
    )

    def notification_db_check() -> str:
        try:
            selected_notification_service.ping()
            return "ready"
        except Exception:
            return "not_ready"

    probes.append(
        ReadinessProbe(
            name="notification_db_readiness",
            is_critical=True,
            check=notification_db_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        )
    )

    def failure_memory_db_check() -> str:
        try:
            selected_failure_case_service.ping()
            return "ready"
        except Exception:
            return "not_ready"

    probes.append(
        ReadinessProbe(
            name="failure_memory_db_readiness",
            is_critical=True,
            check=failure_memory_db_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        )
    )

    if selected_project_memory_service is not None:
        def project_memory_db_check() -> str:
            try:
                selected_project_memory_service.ping()
                return "ready"
            except Exception:
                return "not_ready"

        probes.append(
            ReadinessProbe(
                name="project_memory_db_readiness",
                is_critical=True,
                check=project_memory_db_check,
                timeout_seconds=settings.readiness_timeout_seconds,
            )
        )

    probes.append(
        ReadinessProbe(
            name="model_ledger_readiness",
            is_critical=(
                settings.model_routing_mode == "active"
            ),
            check=lambda: (
                model_gateway.ledger.ping() or "ready"
            ),
            timeout_seconds=settings.readiness_timeout_seconds,
        )
    )

    readiness_service = ReadinessService(
        "api",
        probes,
        max_workers=settings.readiness_probe_workers,
    )

    @app.middleware("http")
    async def observability_middleware(
        request: Request,
        call_next,
    ):
        request_id = (
            request.headers.get(
                "X-Request-ID"
            )
            or uuid4().hex
        )[:200]
        request.state.request_id = request_id

        try:
            with bind_telemetry_context(request_id=request_id):
                with telemetry.span(
                    "http.request",
                    attributes={
                        "http.method": request.method,
                    },
                ) as request_span:
                    start_time = time.monotonic()
                    response = await call_next(request)
                    elapsed = (
                        time.monotonic() - start_time
                    )

                    status_code = response.status_code
                    status_class = (
                        f"{str(status_code)[0]}xx"
                    )

                    # 使用 route template 而不是真实 path，
                    # 避免 /v1/jobs/{job_id} 产生高基数 metric。
                    route_template = getattr(
                        request.scope.get("route"),
                        "path",
                        "unmatched",
                    )

                    # span 在 call_next 之后才有匹配的 route；
                    # 这里补记 http.route，不把真实 path 冒充为 route。
                    try:
                        request_span.set_attribute(
                            "http.route",
                            route_template,
                        )
                    except Exception:
                        pass

                    try:
                        telemetry.counter(
                            "paper_copilot_http_requests_total",
                            1,
                            {
                                "method": request.method,
                                "route": route_template,
                                "status_class": status_class,
                            },
                        )
                    except Exception:
                        pass

                    try:
                        telemetry.histogram(
                            "paper_copilot_http_request_duration_seconds",
                            elapsed,
                            {
                                "method": request.method,
                                "route": route_template,
                                "status_class": status_class,
                            },
                        )
                    except Exception:
                        pass

                    # Phase 30 最小安全响应头。
                    response.headers[
                        "X-Content-Type-Options"
                    ] = "nosniff"
                    response.headers[
                        "Referrer-Policy"
                    ] = "no-referrer"
                    response.headers[
                        "X-Frame-Options"
                    ] = "DENY"
                    if (
                        settings.web_ui_required
                        and "Content-Security-Policy"
                        not in response.headers
                    ):
                        response.headers[
                            "Content-Security-Policy"
                        ] = (
                            "default-src 'self'; "
                            "script-src 'self'; "
                            "style-src 'self'; "
                            "font-src 'self'; "
                            "img-src 'self' data:; "
                            "connect-src 'self'; "
                            "frame-ancestors 'none'"
                        )

                    response.headers[
                        "X-Request-ID"
                    ] = request_id
                    return response
        except Exception:
            raise

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        # liveness 不查询 Provider、Graph 或 worker。
        return {"status": "ok"}

    @app.get("/livez")
    def livez() -> dict:
        build_liveness_probe()
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/readyz")
    def readyz() -> Response:
        report = readiness_service.cached_report()
        status_code = 200 if report.status in {"ready", "degraded"} else 503
        return Response(
            content=json.dumps(report.model_dump()),
            status_code=status_code,
            media_type="application/json",
        )

    # Phase 53 state must exist before router registration checks it.
    app.state.mcp_evidence_repository = None
    if settings.mcp_gateway_enabled:
        from app.mcp_gateway.repository import (
            SqliteMcpEvidenceRepository,
        )

        mcp_repository = SqliteMcpEvidenceRepository(
            settings.mcp_gateway_db_path
        )
        mcp_repository.initialize()
        app.state.mcp_evidence_repository = mcp_repository

    app.include_router(router)
    app.include_router(notification_router)
    app.include_router(resource_router)
    app.include_router(ui_router)
    app.include_router(chat_router)
    app.include_router(retention_router)
    app.include_router(comparison_router)
    app.include_router(rerun_router)
    app.include_router(failure_case_router)
    app.include_router(project_memory_router)
    if selected_knowledge_service is not None:
        app.include_router(knowledge_router)
    app.include_router(model_routing_router)
    if selected_research_browser_service is not None:
        app.include_router(research_browser_router)
    if app.state.mcp_evidence_repository is not None:
        from app.api.mcp_gateway_routes import router as mcp_gateway_router

        app.include_router(mcp_gateway_router)
    install_error_handlers(app)

    # SPA 静态文件必须最后 mount，避免吞掉 /v1、/docs、/livez 和 /readyz。
    mount_web_ui(
        app,
        dist_dir=settings.web_dist_dir,
        required=settings.web_ui_required,
    )

    # Phase 35 retention state
    from app.job_runtime.factory import build_job_store
    from app.retention.factory import build_retention

    app.state.telemetry = telemetry
    app.state.readiness = readiness_service

    knowledge_repo_for_retention = None
    if selected_knowledge_service is not None:
        knowledge_repo_for_retention = selected_knowledge_service.repository
    app.state.retention_bundle = build_retention(
        job_store=build_job_store() if job_service is None else job_service.store,
        artifact_storage=storage or build_artifact_storage(),
        project_memory_repository=(
            selected_project_memory_service.repository
            if selected_project_memory_service is not None
            else None
        ),
        knowledge_repository=knowledge_repo_for_retention,
    )

    return app
