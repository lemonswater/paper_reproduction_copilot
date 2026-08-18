from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.artifact_delivery.errors import (
    ArtifactExportLimitExceeded,
    ArtifactPreviewUnsupported,
)
from app.comparison.errors import (
    ComparisonConflictError,
    ComparisonIntegrityError,
    ComparisonLimitExceededError,
    ComparisonNotFoundError,
)
from app.failure_memory.errors import (
    FailureCaseConflictError,
    FailureCaseIntegrityError,
    FailureCaseLimitExceededError,
    FailureCaseNotFoundError,
)
from app.interaction.schemas import ApiError
from app.job_runtime.errors import (
    JobBackendUnavailable,
    JobConflictError,
    JobNotFoundError,
    JobStoreError,
)
from app.knowledge_base.errors import (
    KnowledgeConflictError,
    KnowledgeIntegrityError,
    KnowledgeLimitExceededError,
    KnowledgeNotFoundError,
)
from app.model_routing.errors import (
    ModelBudgetExceeded,
    ModelCatalogError,
    ModelLedgerIntegrityError,
    ModelRouteUnavailable,
)
from app.notifications.errors import (
    NotificationConflictError,
    NotificationNotFoundError,
)
from app.project_memory.errors import (
    ProjectFactNotFoundError,
    ProjectMemoryConflictError,
    ProjectMemoryError,
    ProjectMemoryIntegrityError,
    ProjectMemoryLimitExceededError,
    ProjectNotFoundError,
)
from app.retention.errors import (
    RetentionBackendUnsupported,
    RetentionConflict,
    RetentionNotFound,
    RetentionPathUnsafe,
    StorageCapacityExceeded,
)
from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
    RerunExpiredError,
    RerunIntegrityError,
    RerunNotFoundError,
)
from app.research_browser.errors import (
    ResearchConflict,
    ResearchContentRejected,
    ResearchIntegrityError,
    ResearchLimitExceeded,
    ResearchNotFound,
    ResearchPolicyError,
    ResearchResourceCandidateRejected,
    ResearchRobotsDenied,
    ResearchSynthesisRejected,
    ResearchTransportUnavailable,
    ResearchUrlRejected,
)
from app.storage.errors import (
    ArtifactBackendUnavailable,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
)


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    payload = ApiError(
        code=code,
        message=message,
        request_id=getattr(
            request.state,
            "request_id",
            None,
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
    )


def install_error_handlers(
    app: FastAPI,
) -> None:
    """把内部异常映射成稳定 HTTP 语义。"""

    @app.exception_handler(
        JobNotFoundError
    )
    async def handle_not_found(
        request: Request,
        exc: JobNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="JOB_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(
        JobConflictError
    )
    async def handle_conflict(
        request: Request,
        exc: JobConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="JOB_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(
        JobBackendUnavailable
    )
    async def handle_job_backend_unavailable(
        request: Request,
        exc: JobBackendUnavailable,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=503,
            code="JOB_BACKEND_UNAVAILABLE",
            message="任务控制面暂时不可用",
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(
        request: Request,
        exc: ValueError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="INVALID_REQUEST",
            message=str(exc),
        )

    @app.exception_handler(JobStoreError)
    async def handle_store_error(
        request: Request,
        exc: JobStoreError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=500,
            code="JOB_STORE_ERROR",
            message=str(exc),
        )
    @app.exception_handler(
        ArtifactNotFoundError
    )
    async def handle_artifact_not_found(
        request: Request,
        exc: ArtifactNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="ARTIFACT_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactIntegrityError
    )
    async def handle_artifact_integrity(
        request: Request,
        exc: ArtifactIntegrityError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="ARTIFACT_INTEGRITY_ERROR",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactBackendUnavailable
    )
    async def handle_artifact_unavailable(
        request: Request,
        exc: ArtifactBackendUnavailable,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=503,
            code="ARTIFACT_BACKEND_UNAVAILABLE",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactPreviewUnsupported
    )
    async def handle_preview_unsupported(
        request: Request,
        exc: ArtifactPreviewUnsupported,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=415,
            code="ARTIFACT_PREVIEW_UNSUPPORTED",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactExportLimitExceeded
    )
    async def handle_export_limit(
        request: Request,
        exc: ArtifactExportLimitExceeded,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=413,
            code="ARTIFACT_EXPORT_LIMIT_EXCEEDED",
            message=str(exc),
        )

    @app.exception_handler(RetentionNotFound)
    async def handle_retention_not_found(
        request: Request,
        exc: RetentionNotFound,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="RETENTION_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(RetentionConflict)
    async def handle_retention_conflict(
        request: Request,
        exc: RetentionConflict,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RETENTION_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(RetentionPathUnsafe)
    async def handle_retention_path_unsafe(
        request: Request,
        exc: RetentionPathUnsafe,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RETENTION_PATH_UNSAFE",
            message=str(exc),
        )

    @app.exception_handler(RetentionBackendUnsupported)
    async def handle_retention_backend_unsupported(
        request: Request,
        exc: RetentionBackendUnsupported,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=501,
            code="RETENTION_BACKEND_UNSUPPORTED",
            message=str(exc),
        )

    @app.exception_handler(StorageCapacityExceeded)
    async def handle_storage_capacity(
        request: Request,
        exc: StorageCapacityExceeded,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=507,
            code="STORAGE_CAPACITY_EXCEEDED",
            message=str(exc),
        )

    @app.exception_handler(ComparisonNotFoundError)
    async def handle_comparison_not_found(
        request: Request,
        exc: ComparisonNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="COMPARISON_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(ComparisonConflictError)
    async def handle_comparison_conflict(
        request: Request,
        exc: ComparisonConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="COMPARISON_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(ComparisonIntegrityError)
    async def handle_comparison_integrity(
        request: Request,
        exc: ComparisonIntegrityError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="COMPARISON_INTEGRITY_ERROR",
            message=str(exc),
        )

    @app.exception_handler(ComparisonLimitExceededError)
    async def handle_comparison_limit(
        request: Request,
        exc: ComparisonLimitExceededError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=413,
            code="COMPARISON_LIMIT_EXCEEDED",
            message=str(exc),
        )

    @app.exception_handler(RerunNotFoundError)
    async def rerun_not_found_handler(
        request: Request,
        exc: RerunNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="RERUN_PROPOSAL_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(RerunExpiredError)
    async def rerun_expired_handler(
        request: Request,
        exc: RerunExpiredError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RERUN_PROPOSAL_EXPIRED",
            message=str(exc),
        )

    @app.exception_handler(RerunConflictError)
    async def rerun_conflict_handler(
        request: Request,
        exc: RerunConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RERUN_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(RerunCommandRejectedError)
    async def rerun_command_rejected_handler(
        request: Request,
        exc: RerunCommandRejectedError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RERUN_COMMAND_REJECTED",
            message=str(exc),
        )

    @app.exception_handler(RerunIntegrityError)
    async def rerun_integrity_handler(
        request: Request,
        exc: RerunIntegrityError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=500,
            code="RERUN_INTEGRITY_ERROR",
            message="Rerun evidence integrity validation failed",
        )

    @app.exception_handler(NotificationNotFoundError)
    async def handle_notification_not_found(
        request: Request,
        exc: NotificationNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="NOTIFICATION_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(NotificationConflictError)
    async def handle_notification_conflict(
        request: Request,
        exc: NotificationConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="NOTIFICATION_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(FailureCaseNotFoundError)
    async def failure_case_not_found_handler(
        request: Request,
        exc: FailureCaseNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="FAILURE_CASE_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(FailureCaseConflictError)
    async def failure_case_conflict_handler(
        request: Request,
        exc: FailureCaseConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="FAILURE_CASE_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(FailureCaseLimitExceededError)
    async def failure_case_limit_handler(
        request: Request,
        exc: FailureCaseLimitExceededError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=413,
            code="FAILURE_CASE_LIMIT_EXCEEDED",
            message=str(exc),
        )

    @app.exception_handler(FailureCaseIntegrityError)
    async def failure_case_integrity_handler(
        request: Request,
        exc: FailureCaseIntegrityError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=500,
            code="FAILURE_CASE_INTEGRITY_ERROR",
            message="Failure Case evidence integrity validation failed",
        )

    # Phase 46: Project Memory error mapping

    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(
        request: Request,
        exc: ProjectNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="PROJECT_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(ProjectFactNotFoundError)
    async def project_fact_not_found_handler(
        request: Request,
        exc: ProjectFactNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="PROJECT_FACT_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(ProjectMemoryConflictError)
    async def project_memory_conflict_handler(
        request: Request,
        exc: ProjectMemoryConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="PROJECT_MEMORY_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(ProjectMemoryIntegrityError)
    async def project_memory_integrity_handler(
        request: Request,
        exc: ProjectMemoryIntegrityError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=409,
            code="PROJECT_MEMORY_INTEGRITY_ERROR",
            message="Project Memory integrity validation failed",
        )

    @app.exception_handler(ProjectMemoryLimitExceededError)
    async def project_memory_limit_handler(
        request: Request,
        exc: ProjectMemoryLimitExceededError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=413,
            code="PROJECT_MEMORY_LIMIT_EXCEEDED",
            message=str(exc),
        )

    @app.exception_handler(ProjectMemoryError)
    async def project_memory_generic_handler(
        request: Request,
        exc: ProjectMemoryError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=500,
            code="PROJECT_MEMORY_ERROR",
            message="Project Memory operation failed",
        )

    # Phase 49: Knowledge Base error mapping

    @app.exception_handler(KnowledgeNotFoundError)
    async def handle_knowledge_not_found(
        request: Request,
        exc: KnowledgeNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="KNOWLEDGE_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(KnowledgeConflictError)
    async def handle_knowledge_conflict(
        request: Request,
        exc: KnowledgeConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="KNOWLEDGE_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(KnowledgeIntegrityError)
    async def handle_knowledge_integrity(
        request: Request,
        exc: KnowledgeIntegrityError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="KNOWLEDGE_INTEGRITY_ERROR",
            message=str(exc),
        )

    @app.exception_handler(KnowledgeLimitExceededError)
    async def handle_knowledge_limit(
        request: Request,
        exc: KnowledgeLimitExceededError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=413,
            code="KNOWLEDGE_LIMIT_EXCEEDED",
            message=str(exc),
        )

    # Phase 50: Model Routing error mapping

    @app.exception_handler(ModelBudgetExceeded)
    async def handle_model_budget_exceeded(
        request: Request,
        exc: ModelBudgetExceeded,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=429,
            code="MODEL_BUDGET_EXCEEDED",
            message="当前模型调用预算不足，请稍后重试或调整本地预算。",
        )

    @app.exception_handler(ModelRouteUnavailable)
    async def handle_model_route_unavailable(
        request: Request,
        exc: ModelRouteUnavailable,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=503,
            code="MODEL_ROUTE_UNAVAILABLE",
            message="当前没有满足任务要求的可用模型配置。",
        )

    @app.exception_handler(ModelCatalogError)
    async def handle_model_catalog_error(
        request: Request,
        exc: ModelCatalogError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=503,
            code="MODEL_CATALOG_UNAVAILABLE",
            message="模型路由配置当前不可用。",
        )

    @app.exception_handler(ModelLedgerIntegrityError)
    async def handle_model_ledger_integrity(
        request: Request,
        exc: ModelLedgerIntegrityError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=503,
            code="MODEL_LEDGER_UNAVAILABLE",
            message="模型预算账本当前不可用。",
        )

    # Phase 51: Research Browser error mapping

    @app.exception_handler(ResearchNotFound)
    async def handle_research_not_found(
        request: Request,
        exc: ResearchNotFound,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="RESEARCH_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(ResearchConflict)
    async def handle_research_conflict(
        request: Request,
        exc: ResearchConflict,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RESEARCH_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(ResearchPolicyError)
    async def handle_research_policy(
        request: Request,
        exc: ResearchPolicyError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_POLICY_REJECTED",
            message=str(exc),
        )

    @app.exception_handler(ResearchUrlRejected)
    async def handle_research_url_rejected(
        request: Request,
        exc: ResearchUrlRejected,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_POLICY_REJECTED",
            message=str(exc),
        )

    @app.exception_handler(ResearchRobotsDenied)
    async def handle_research_robots_denied(
        request: Request,
        exc: ResearchRobotsDenied,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_CONTENT_REJECTED",
            message=str(exc),
        )

    @app.exception_handler(ResearchContentRejected)
    async def handle_research_content_rejected(
        request: Request,
        exc: ResearchContentRejected,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_CONTENT_REJECTED",
            message=str(exc),
        )

    @app.exception_handler(ResearchLimitExceeded)
    async def handle_research_limit(
        request: Request,
        exc: ResearchLimitExceeded,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_LIMIT_EXCEEDED",
            message=str(exc),
        )

    @app.exception_handler(ResearchTransportUnavailable)
    async def handle_research_transport(
        request: Request,
        exc: ResearchTransportUnavailable,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=502,
            code="RESEARCH_FETCH_FAILED",
            message=str(exc),
        )

    @app.exception_handler(ResearchIntegrityError)
    async def handle_research_integrity(
        request: Request,
        exc: ResearchIntegrityError,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=500,
            code="RESEARCH_INTEGRITY_FAILED",
            message="Research evidence integrity validation failed",
        )

    @app.exception_handler(ResearchSynthesisRejected)
    async def handle_research_synthesis_rejected(
        request: Request,
        exc: ResearchSynthesisRejected,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_SYNTHESIS_REJECTED",
            message=str(exc),
        )

    @app.exception_handler(ResearchResourceCandidateRejected)
    async def handle_research_resource_candidate_rejected(
        request: Request,
        exc: ResearchResourceCandidateRejected,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="RESEARCH_RESOURCE_CANDIDATE_REJECTED",
            message=str(exc),
        )