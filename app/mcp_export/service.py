from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import PurePosixPath
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.artifact_delivery.errors import ArtifactPreviewUnsupported
from app.artifact_delivery.service import ArtifactDeliveryService
from app.interaction.service import InteractionService
from app.job_runtime.errors import JobConflictError, JobNotFoundError
from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.errors import (
    McpExportError,
    McpExportEvidenceUnavailable,
    McpExportFinalReportNotFound,
    McpExportIntegrityError,
    McpExportInternalError,
    McpExportJobNotFound,
)
from app.mcp_export.identity import (
    bounded_limit,
    normalize_query,
    sha256_text,
    sha256_value,
    validate_job_id,
)
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter
from app.mcp_export.schemas import (
    McpExportArtifact,
    McpExportArtifactPage,
    McpExportAuditRecord,
    McpExportCitation,
    McpExportEvidenceItem,
    McpExportEvidencePack,
    McpExportFinalReport,
    McpExportJobStatus,
)
from app.secrets.redaction import SecretRedactor
from app.storage.errors import ArtifactIntegrityError
from app.tool_calling.schemas import EvidenceToolOutput
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ToolInvocationContext


ExportResult = TypeVar("ExportResult", bound=BaseModel)

LOCAL_ACTOR = "mcp-export:local-token"
LOCAL_CAPABILITIES = {
    "job.read.current",
    "run.read.evidence",
}
LOCAL_EVIDENCE_TYPES = [
    "job",
    "event",
    "artifact",
    "log",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("code") or value.get("error_code")
    if raw is None:
        return None
    normalized = str(raw).strip()
    return normalized[:100] or None


def _map_export_error(exc: BaseException) -> McpExportError:
    if isinstance(exc, McpExportError):
        return exc
    if isinstance(exc, JobNotFoundError):
        return McpExportJobNotFound("job not found")
    if isinstance(exc, ArtifactPreviewUnsupported):
        return McpExportFinalReportNotFound("report is not previewable")
    if isinstance(exc, (JobConflictError, ArtifactIntegrityError)):
        return McpExportIntegrityError("evidence identity mismatch")
    return McpExportInternalError("unexpected export failure")


class ReadOnlyMcpExportService:
    def __init__(
        self,
        *,
        interaction: InteractionService,
        artifact_delivery: ArtifactDeliveryService,
        evidence_registry: ToolRegistry,
        audit_repository: SqliteMcpExportAuditRepository,
        rate_limiter: InMemoryMcpExportRateLimiter,
        redactor: SecretRedactor,
        max_artifacts: int,
        max_report_chars: int,
    ) -> None:
        self.interaction = interaction
        self.artifact_delivery = artifact_delivery
        self.evidence_registry = evidence_registry
        self.audit_repository = audit_repository
        self.rate_limiter = rate_limiter
        self.redactor = redactor
        self.max_artifacts = max_artifacts
        self.max_report_chars = max_report_chars
        self.actor_fingerprint = sha256_text(LOCAL_ACTOR)

    def _execute(
        self,
        *,
        operation: str,
        job_id: str,
        request_id: str,
        input_payload: dict,
        function: Callable[[], ExportResult],
    ) -> ExportResult:
        """统一处理预算、错误收敛和 Hash-only Audit。"""

        started_at = utc_now()
        started = perf_counter()
        input_sha256 = sha256_value(input_payload)

        try:
            # 限流也属于受审计的调用结果，必须放在 try 内。
            self.rate_limiter.acquire(self.actor_fingerprint)
            output = function()
        except Exception as exc:
            mapped = _map_export_error(exc)
            record = McpExportAuditRecord(
                call_id=f"mcpexportcall_{uuid4().hex[:24]}",
                request_id=request_id,
                actor_fingerprint=self.actor_fingerprint,
                operation=operation,
                job_id=job_id,
                status="failed",
                input_sha256=input_sha256,
                error_code=mapped.code,
                started_at=started_at,
                finished_at=utc_now(),
                duration_ms=(perf_counter() - started) * 1000,
            )
            self.audit_repository.put(record)
            raise mapped from None

        record = McpExportAuditRecord(
            call_id=f"mcpexportcall_{uuid4().hex[:24]}",
            request_id=request_id,
            actor_fingerprint=self.actor_fingerprint,
            operation=operation,
            job_id=job_id,
            status="succeeded",
            input_sha256=input_sha256,
            output_sha256=sha256_value(output),
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
        )
        # Audit 是安全边界；持久化失败时不向 Client 声称调用成功。
        self.audit_repository.put(record)
        return output

    def get_status(
        self,
        *,
        job_id: str,
        request_id: str,
        operation: str = "get_reproduction_status",
    ) -> McpExportJobStatus:
        selected_job_id = validate_job_id(job_id)

        def build() -> McpExportJobStatus:
            view = self.interaction.get_job(selected_job_id)
            result = view.result
            payload = {
                "schema_version": "phase54-v1",
                "job_id": view.job_id,
                "run_id": view.run_id,
                "status": view.status,
                "version": view.version,
                "attempt_count": view.attempt_count,
                "max_attempts": view.max_attempts,
                # cancel/rerun 也属于 allowed_operation，不能据此判断等待用户。
                "waiting_for_user": view.status == "waiting_for_input",
                "allowed_operation_kinds": sorted(
                    {item.kind for item in view.allowed_operations}
                ),
                "final_status": (
                    result.final_status if result is not None else None
                ),
                "stage_error_count": (
                    result.stage_error_count if result is not None else None
                ),
                "output_file_count": (
                    result.output_file_count if result is not None else None
                ),
                "has_error": view.error is not None,
                "error_code": _error_code(view.error),
                "created_at": view.created_at,
                "updated_at": view.updated_at,
            }
            return McpExportJobStatus(
                **payload,
                snapshot_sha256=sha256_value(payload),
            )

        return self._execute(
            operation=operation,
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={"job_id": selected_job_id},
            function=build,
        )

    def list_artifacts(
        self,
        *,
        job_id: str,
        limit: int,
        request_id: str,
    ) -> McpExportArtifactPage:
        selected_job_id = validate_job_id(job_id)
        selected_limit = bounded_limit(
            limit,
            maximum=self.max_artifacts,
        )

        def build() -> McpExportArtifactPage:
            internal_job = self.interaction.job_service.get(selected_job_id)
            views = self.artifact_delivery.list_views(internal_job)
            selected = views[:selected_limit]
            items = [
                McpExportArtifact(
                    artifact_id=item.artifact_id,
                    run_id=item.run_id,
                    # 只返回 basename，不返回 relative_path。
                    display_name=PurePosixPath(item.relative_path).name,
                    layer=item.layer,
                    media_type=item.media_type,
                    sha256=item.sha256,
                    size_bytes=item.size_bytes,
                    producer_node=item.producer_node,
                    created_at=item.created_at,
                    preview_supported=item.preview_supported,
                )
                for item in selected
            ]
            payload = {
                "schema_version": "phase54-v1",
                "job_id": internal_job.job_id,
                "run_id": internal_job.run_id,
                "items": [
                    item.model_dump(mode="json") for item in items
                ],
                "returned_count": len(items),
                "truncated": len(views) > len(items),
            }
            return McpExportArtifactPage(
                **payload,
                snapshot_sha256=sha256_value(payload),
            )

        return self._execute(
            operation="list_reproduction_artifacts",
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={
                "job_id": selected_job_id,
                "limit": selected_limit,
            },
            function=build,
        )

    @staticmethod
    def _final_report_priority(relative_path: str) -> tuple[int, str]:
        """服务端识别 final_report；Client 不能提交路径。"""

        normalized = relative_path.replace("\\", "/").lower()
        preferred = {
            "reports/final_report.md": 0,
            "outputs/final_report.md": 1,
            "final_report.md": 2,
        }
        return preferred.get(normalized, 10), normalized

    def read_final_report(
        self,
        *,
        job_id: str,
        request_id: str,
        operation: str = "read_reproduction_final_report",
    ) -> McpExportFinalReport:
        selected_job_id = validate_job_id(job_id)

        def build() -> McpExportFinalReport:
            internal_job = self.interaction.job_service.get(selected_job_id)
            views = self.artifact_delivery.list_views(internal_job)
            candidates = [
                item
                for item in views
                if PurePosixPath(item.relative_path).name.lower()
                == "final_report.md"
                and item.media_type in {"text/markdown", "text/plain"}
                and item.preview_supported
            ]
            if not candidates:
                raise McpExportFinalReportNotFound("no final report")

            selected = sorted(
                candidates,
                key=lambda item: self._final_report_priority(
                    item.relative_path
                ),
            )[0]
            preview = self.artifact_delivery.preview(
                job=internal_job,
                artifact_id=selected.artifact_id,
            )
            raw_content = preview.content[: self.max_report_chars]
            content = self.redactor.redact_text(
                raw_content,
                max_chars=self.max_report_chars,
            )
            truncated = (
                preview.truncated
                or len(preview.content) > len(raw_content)
            )
            payload = {
                "schema_version": "phase54-v1",
                "job_id": internal_job.job_id,
                "run_id": internal_job.run_id,
                "artifact_id": selected.artifact_id,
                "artifact_sha256": selected.sha256,
                "media_type": selected.media_type,
                "total_size_bytes": preview.total_size_bytes,
                "returned_chars": len(content),
                "truncated": truncated,
                "content": content,
                "content_sha256": sha256_text(content),
            }
            return McpExportFinalReport(
                **payload,
                snapshot_sha256=sha256_value(payload),
            )

        return self._execute(
            operation=operation,
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={"job_id": selected_job_id},
            function=build,
        )

    @staticmethod
    def _public_citation(item) -> McpExportCitation:
        citation = item.citation
        source_type = citation.source_type
        if source_type not in LOCAL_EVIDENCE_TYPES:
            raise McpExportEvidenceUnavailable(
                "transitive evidence type is not exportable"
            )

        if source_type == "artifact":
            label = f"artifact:{citation.artifact_id or 'unknown'}"
        elif source_type == "event":
            label = f"job-event:{citation.event_id or 0}"
        elif source_type == "log":
            label = "bounded-job-log"
        else:
            label = "current-job-status"

        return McpExportCitation(
            citation_id=citation.citation_id,
            source_type=source_type,
            label=label,
            artifact_id=citation.artifact_id,
            artifact_sha256=citation.artifact_sha256,
            event_id=citation.event_id,
        )

    def search_evidence(
        self,
        *,
        job_id: str,
        query: str,
        limit: int,
        request_id: str,
    ) -> McpExportEvidencePack:
        selected_job_id = validate_job_id(job_id)
        selected_query = normalize_query(query)
        selected_limit = bounded_limit(limit, maximum=6)

        def build() -> McpExportEvidencePack:
            result = self.evidence_registry.invoke(
                name="chat.search_reproduction_evidence",
                raw_input={
                    "query": selected_query,
                    # 固定本地来源，禁止 web/mcp/knowledge 等传递能力。
                    "source_types": list(LOCAL_EVIDENCE_TYPES),
                    "limit": selected_limit,
                },
                context=ToolInvocationContext(
                    actor=LOCAL_ACTOR,
                    request_id=request_id,
                    caller_kind="agent",
                    job_id=selected_job_id,
                    granted_capabilities=set(LOCAL_CAPABILITIES),
                ),
            )
            if result.failure is not None or result.output is None:
                code = (
                    result.failure.code
                    if result.failure is not None
                    else "TOOL_EMPTY_RESULT"
                )
                raise McpExportEvidenceUnavailable(code)

            evidence = EvidenceToolOutput.model_validate(result.output)
            items = []
            for item in evidence.items[:selected_limit]:
                excerpt = self.redactor.redact_text(
                    item.content,
                    max_chars=4000,
                )
                if not excerpt.strip():
                    continue
                items.append(
                    McpExportEvidenceItem(
                        citation=self._public_citation(item),
                        excerpt=excerpt,
                        excerpt_sha256=sha256_text(excerpt),
                    )
                )

            payload = {
                "schema_version": "phase54-v1",
                "job_id": selected_job_id,
                "query_sha256": sha256_text(selected_query),
                "items": [
                    item.model_dump(mode="json") for item in items
                ],
                "truncated": evidence.truncated,
            }
            return McpExportEvidencePack(
                **payload,
                pack_sha256=sha256_value(payload),
            )

        return self._execute(
            operation="search_reproduction_evidence",
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={
                "job_id": selected_job_id,
                "query_sha256": sha256_text(selected_query),
                "limit": selected_limit,
                "source_types": list(LOCAL_EVIDENCE_TYPES),
            },
            function=build,
        )
