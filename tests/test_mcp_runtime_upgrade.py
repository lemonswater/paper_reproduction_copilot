from __future__ import annotations

from datetime import datetime, timezone

from app.config import settings
from app.mcp_operations.identity import runtime_report_hash
from app.mcp_operations.policy import load_runtime_policy
from app.mcp_operations.schemas import (
    McpInvocationSample,
    McpOperationSummary,
    McpRuntimeProfileResult,
    McpRuntimeReport,
)
from app.mcp_operations.upgrade import compare_runtime_reports


SURFACE_SHA256 = "a" * 64
BASELINE_SHA256 = "b" * 64


def _report(*, report_id: str, p95_ms: float) -> McpRuntimeReport:
    sample = McpInvocationSample(
        profile_id="in-memory-modern",
        operation="get_reproduction_status",
        kind="tool",
        sample_index=0,
        status="succeeded",
        duration_ms=p95_ms,
        output_sha256="c" * 64,
    )
    summary = McpOperationSummary(
        profile_id="in-memory-modern",
        operation="get_reproduction_status",
        kind="tool",
        sample_count=1,
        success_count=1,
        success_rate=1.0,
        p95_ms=p95_ms,
        passed=True,
    )
    policy = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    report = McpRuntimeReport(
        report_id=report_id,
        mode="release",
        generated_at=datetime.now(timezone.utc).isoformat(),
        policy_sha256=policy.policy_sha256,
        baseline_sha256=BASELINE_SHA256,
        passed=True,
        profiles=[
            McpRuntimeProfileResult(
                profile_id="in-memory-modern",
                surface_sha256=SURFACE_SHA256,
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


def test_upgrade_rejects_large_latency_regression() -> None:
    policy = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    comparison = compare_runtime_reports(
        before=_report(
            report_id="mcpruntime_1111111111111111",
            p95_ms=10,
        ),
        after=_report(
            report_id="mcpruntime_2222222222222222",
            p95_ms=800,
        ),
        policy=policy,
        accepted_surface_sha256=SURFACE_SHA256,
    )
    assert comparison.passed is False
    assert "mcp_upgrade_operation_regression" in (
        comparison.finding_codes
    )


def test_upgrade_accepts_small_local_jitter() -> None:
    policy = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    comparison = compare_runtime_reports(
        before=_report(
            report_id="mcpruntime_3333333333333333",
            p95_ms=10,
        ),
        after=_report(
            report_id="mcpruntime_4444444444444444",
            p95_ms=15,
        ),
        policy=policy,
        accepted_surface_sha256=SURFACE_SHA256,
    )
    assert comparison.passed is True
