from __future__ import annotations

from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.schemas import McpExportAuditRecord


def _record(job_id: str) -> McpExportAuditRecord:
    return McpExportAuditRecord(
        call_id="mcpexportcall_" + "a" * 24,
        request_id="request-1",
        actor_fingerprint="b" * 64,
        operation="get_reproduction_status",
        job_id=job_id,
        status="succeeded",
        input_sha256="c" * 64,
        output_sha256="d" * 64,
        started_at="2026-08-14T00:00:00+00:00",
        finished_at="2026-08-14T00:00:01+00:00",
        duration_ms=1.0,
    )


def test_audit_round_trip_and_delete(tmp_path) -> None:
    job_id = "job_" + "e" * 32
    repository = SqliteMcpExportAuditRepository(
        tmp_path / "audit.sqlite"
    )
    repository.initialize()
    repository.put(_record(job_id))

    assert repository.list_for_job(job_id) == [_record(job_id)]
    assert repository.delete_for_job(job_id) == 1
    assert repository.delete_for_job(job_id) == 0
    assert repository.list_for_job(job_id) == []


def test_audit_database_does_not_store_raw_payload(tmp_path) -> None:
    path = tmp_path / "audit.sqlite"
    repository = SqliteMcpExportAuditRepository(path)
    repository.initialize()
    repository.put(_record("job_" + "f" * 32))

    raw = path.read_bytes()
    assert b"Bearer " not in raw
    assert b"failure reason from user" not in raw
