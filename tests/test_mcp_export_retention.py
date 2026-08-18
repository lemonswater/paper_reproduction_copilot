from __future__ import annotations

from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.schemas import McpExportAuditRecord


def test_export_audit_satisfies_retention_port(tmp_path) -> None:
    job_id = "job_" + "a" * 32
    repository = SqliteMcpExportAuditRepository(
        tmp_path / "audit.sqlite"
    )
    repository.initialize()
    repository.put(
        McpExportAuditRecord(
            call_id="mcpexportcall_" + "b" * 24,
            request_id="request-1",
            actor_fingerprint="c" * 64,
            operation="resource_job_status",
            job_id=job_id,
            status="succeeded",
            input_sha256="d" * 64,
            output_sha256="e" * 64,
            started_at="2026-08-14T00:00:00+00:00",
            finished_at="2026-08-14T00:00:01+00:00",
            duration_ms=1.0,
        )
    )

    assert repository.delete_for_job(job_id) == 1
    assert repository.list_for_job(job_id) == []
