from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.chat.schemas import ChatCitation
from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter
from app.mcp_export.service import ReadOnlyMcpExportService
from app.secrets.redaction import SecretRedactor
from app.tool_calling.schemas import (
    EvidenceToolOutput,
    ToolEvidenceItem,
)


JOB_ID = "job_" + "a" * 32
RUN_ID = "run_phase54_test"
ARTIFACT_ID = "artifact_final_report"
ARTIFACT_SHA256 = "b" * 64
SECRET_VALUE = "phase54-sensitive-token-1234567890"


class FakeInteraction:
    def __init__(self) -> None:
        self.internal_job = SimpleNamespace(
            job_id=JOB_ID,
            run_id=RUN_ID,
        )
        self.job_service = SimpleNamespace(
            get=self._get_internal_job,
        )

    def _get_internal_job(self, job_id: str):
        if job_id != JOB_ID:
            from app.job_runtime.errors import JobNotFoundError

            raise JobNotFoundError(job_id)
        return self.internal_job

    def get_job(self, job_id: str):
        self._get_internal_job(job_id)
        return SimpleNamespace(
            job_id=JOB_ID,
            run_id=RUN_ID,
            status="waiting_for_input",
            version=7,
            attempt_count=1,
            max_attempts=3,
            allowed_operations=[
                SimpleNamespace(kind="submit_decision")
            ],
            result=SimpleNamespace(
                final_status=None,
                stage_error_count=1,
                output_file_count=8,
            ),
            error={"code": "TRAINING_FAILED", "message": "hidden"},
            created_at="2026-08-14T00:00:00+00:00",
            updated_at="2026-08-14T00:01:00+00:00",
        )


class FakeArtifactDelivery:
    def __init__(self) -> None:
        self.views = [
            SimpleNamespace(
                artifact_id=ARTIFACT_ID,
                run_id=RUN_ID,
                layer="report",
                relative_path="reports/final_report.md",
                media_type="text/markdown",
                sha256=ARTIFACT_SHA256,
                size_bytes=36,
                producer_node="final_report",
                created_at="2026-08-14T00:02:00+00:00",
                preview_supported=True,
            )
        ]

    def list_views(self, _job):
        return list(self.views)

    def preview(self, *, job, artifact_id: str):
        assert job.job_id == JOB_ID
        assert artifact_id == ARTIFACT_ID
        content = (
            "# Final report\n\nEvidence-grounded result.\n"
            f"API_TOKEN={SECRET_VALUE}"
        )
        return SimpleNamespace(
            artifact_id=ARTIFACT_ID,
            media_type="text/markdown",
            sha256=ARTIFACT_SHA256,
            total_size_bytes=len(content.encode("utf-8")),
            returned_bytes=len(content.encode("utf-8")),
            truncated=False,
            content=content,
        )


class FakeEvidenceRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        output = EvidenceToolOutput(
            summary="matching evidence",
            items=[
                ToolEvidenceItem(
                    citation=ChatCitation(
                        citation_id=(
                            f"artifact:{ARTIFACT_ID}:1"
                        ),
                        source_type="artifact",
                        label="reports/final_report.md",
                        artifact_id=ARTIFACT_ID,
                        relative_path="reports/final_report.md",
                        artifact_sha256=ARTIFACT_SHA256,
                        locator="chunk 1",
                    ),
                    content=(
                        "The run stopped before training completed. "
                        f"Bearer {SECRET_VALUE}"
                    ),
                )
            ],
            truncated=False,
        )
        return SimpleNamespace(
            output=output.model_dump(mode="json"),
            failure=None,
        )


def build_test_service(
    tmp_path: Path,
) -> tuple[
    ReadOnlyMcpExportService,
    SqliteMcpExportAuditRepository,
    FakeArtifactDelivery,
    FakeEvidenceRegistry,
]:
    audit = SqliteMcpExportAuditRepository(
        tmp_path / "mcp_export_audit.sqlite"
    )
    audit.initialize()
    delivery = FakeArtifactDelivery()
    registry = FakeEvidenceRegistry()
    service = ReadOnlyMcpExportService(
        interaction=FakeInteraction(),
        artifact_delivery=delivery,
        evidence_registry=registry,
        audit_repository=audit,
        rate_limiter=InMemoryMcpExportRateLimiter(
            max_calls_per_minute=100
        ),
        redactor=SecretRedactor.from_values([SECRET_VALUE]),
        max_artifacts=50,
        max_report_chars=50000,
    )
    return service, audit, delivery, registry
