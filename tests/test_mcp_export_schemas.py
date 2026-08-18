from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.mcp_export.identity import (
    normalize_query,
    validate_job_id,
)
from app.mcp_export.schemas import (
    McpExportArtifact,
    McpExportAuditRecord,
)


def test_validate_job_id_accepts_only_generated_identity() -> None:
    valid = "job_" + "a" * 32
    assert validate_job_id(valid) == valid

    for invalid in [
        "job_test",
        "../job_" + "a" * 32,
        "job_" + "A" * 32,
        "job_" + "a" * 31,
    ]:
        with pytest.raises(Exception):
            validate_job_id(invalid)


def test_normalize_query_rejects_control_characters() -> None:
    assert normalize_query("  failure   reason ") == "failure reason"
    with pytest.raises(Exception):
        normalize_query("failure\x00reason")


def test_artifact_projection_rejects_path_like_display_name() -> None:
    with pytest.raises(ValidationError):
        McpExportArtifact(
            artifact_id="artifact_1",
            run_id="run_1",
            display_name="reports/final_report.md",
            layer="report",
            media_type="text/markdown",
            sha256="a" * 64,
            size_bytes=10,
            producer_node="final_report",
            created_at="2026-08-14T00:00:00+00:00",
            preview_supported=True,
        )


def test_success_audit_requires_output_hash() -> None:
    with pytest.raises(ValidationError):
        McpExportAuditRecord(
            call_id="mcpexportcall_" + "a" * 24,
            request_id="request-1",
            actor_fingerprint="b" * 64,
            operation="get_reproduction_status",
            job_id="job_" + "c" * 32,
            status="succeeded",
            input_sha256="d" * 64,
            output_sha256=None,
            started_at="2026-08-14T00:00:00+00:00",
            finished_at="2026-08-14T00:00:01+00:00",
            duration_ms=1.0,
        )
