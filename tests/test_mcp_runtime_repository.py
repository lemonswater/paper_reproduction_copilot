from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.mcp_operations.errors import McpRuntimeReportInvalid
from app.mcp_operations.identity import runtime_report_hash
from app.mcp_operations.repository import (
    load_runtime_report,
    write_runtime_report,
)
from app.mcp_operations.schemas import (
    McpInvocationSample,
    McpOperationSummary,
    McpRuntimeProfileResult,
    McpRuntimeReport,
)


def _report() -> McpRuntimeReport:
    sample = McpInvocationSample(
        profile_id="in-memory-modern",
        operation="get_reproduction_status",
        kind="tool",
        sample_index=0,
        status="succeeded",
        duration_ms=2.0,
        output_sha256="a" * 64,
    )
    summary = McpOperationSummary(
        profile_id="in-memory-modern",
        operation="get_reproduction_status",
        kind="tool",
        sample_count=1,
        success_count=1,
        success_rate=1.0,
        p95_ms=2.0,
        passed=True,
    )
    report = McpRuntimeReport(
        report_id="mcpruntime_1111111111111111",
        mode="release",
        generated_at=datetime.now(timezone.utc).isoformat(),
        policy_sha256="b" * 64,
        baseline_sha256="c" * 64,
        passed=True,
        profiles=[
            McpRuntimeProfileResult(
                profile_id="in-memory-modern",
                surface_sha256="d" * 64,
                operation_summaries=[summary],
                passed=True,
            )
        ],
        samples=[sample],
        report_sha256="0" * 64,
    )
    return report.model_copy(
        update={"report_sha256": runtime_report_hash(report)}
    )


def test_repository_round_trips_hash_bound_report(tmp_path) -> None:
    root = tmp_path / "analysis" / "mcp_runtime"
    report = _report()
    json_path, markdown_path = write_runtime_report(
        root=root,
        report=report,
    )

    loaded = load_runtime_report(json_path, root=root)
    assert loaded == report
    assert markdown_path.is_file()
    assert report.report_sha256 in markdown_path.read_text(
        encoding="utf-8"
    )


def test_repository_rejects_tampered_report(tmp_path) -> None:
    root = tmp_path / "analysis" / "mcp_runtime"
    json_path, _markdown_path = write_runtime_report(
        root=root,
        report=_report(),
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["passed"] = False
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(McpRuntimeReportInvalid):
        load_runtime_report(json_path, root=root)


def test_repository_rejects_path_outside_report_root(tmp_path) -> None:
    root = tmp_path / "analysis" / "mcp_runtime"
    outside = tmp_path / "outside" / "report.json"
    outside.parent.mkdir()
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(McpRuntimeReportInvalid):
        load_runtime_report(outside, root=root)
