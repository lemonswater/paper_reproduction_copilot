from __future__ import annotations

import pytest

from app.mcp_export.errors import McpExportFinalReportNotFound
from app.mcp_export.identity import sha256_text
from tests.mcp_export_helpers import (
    ARTIFACT_ID,
    JOB_ID,
    SECRET_VALUE,
    build_test_service,
)


def test_status_is_a_narrow_public_projection(tmp_path) -> None:
    service, audit, _delivery, _registry = build_test_service(tmp_path)

    status = service.get_status(
        job_id=JOB_ID,
        request_id="request-status",
    )

    payload = status.model_dump(mode="json")
    assert status.waiting_for_user is True
    assert status.error_code == "TRAINING_FAILED"
    assert "run_dir" not in payload
    assert "thread_id" not in payload
    assert "claim_token" not in payload
    assert "message" not in payload
    assert len(audit.list_for_job(JOB_ID)) == 1


def test_artifacts_do_not_export_relative_path(tmp_path) -> None:
    service, _audit, _delivery, _registry = build_test_service(tmp_path)

    page = service.list_artifacts(
        job_id=JOB_ID,
        limit=20,
        request_id="request-artifacts",
    )

    assert page.items[0].artifact_id == ARTIFACT_ID
    assert page.items[0].display_name == "final_report.md"
    serialized = page.model_dump_json()
    assert "reports/final_report.md" not in serialized
    assert "relative_path" not in serialized
    assert "object_key" not in serialized


def test_final_report_is_server_selected_and_hash_bound(tmp_path) -> None:
    service, _audit, _delivery, _registry = build_test_service(tmp_path)

    report = service.read_final_report(
        job_id=JOB_ID,
        request_id="request-report",
    )

    assert report.artifact_id == ARTIFACT_ID
    assert report.content_sha256 == sha256_text(report.content)
    assert report.content.startswith("# Final report")
    assert SECRET_VALUE not in report.content
    assert "<redacted>" in report.content


def test_missing_final_report_is_a_stable_error(tmp_path) -> None:
    service, audit, delivery, _registry = build_test_service(tmp_path)
    delivery.views = []

    with pytest.raises(McpExportFinalReportNotFound):
        service.read_final_report(
            job_id=JOB_ID,
            request_id="request-no-report",
        )

    records = audit.list_for_job(JOB_ID)
    assert records[0].error_code == "MCP_EXPORT_FINAL_REPORT_NOT_FOUND"


def test_evidence_uses_only_local_source_types(tmp_path) -> None:
    service, _audit, _delivery, registry = build_test_service(tmp_path)

    pack = service.search_evidence(
        job_id=JOB_ID,
        query="Why did training fail?",
        limit=3,
        request_id="request-evidence",
    )

    raw_input = registry.calls[0]["raw_input"]
    assert raw_input["source_types"] == [
        "job",
        "event",
        "artifact",
        "log",
    ]
    assert "mcp" not in raw_input["source_types"]
    assert "web" not in raw_input["source_types"]
    assert pack.items[0].citation.label == f"artifact:{ARTIFACT_ID}"
    assert "reports/final_report.md" not in pack.model_dump_json()
    assert SECRET_VALUE not in pack.model_dump_json()
    assert "<redacted>" in pack.items[0].excerpt
