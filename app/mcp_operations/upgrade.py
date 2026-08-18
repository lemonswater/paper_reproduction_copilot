from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.mcp_operations.identity import upgrade_comparison_hash
from app.mcp_operations.schemas import (
    McpOperationSummary,
    McpRuntimePolicy,
    McpRuntimeReport,
    McpUpgradeComparison,
    McpUpgradeOperationComparison,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary_map(
    report: McpRuntimeReport,
) -> dict[tuple[str, str], McpOperationSummary]:
    return {
        (profile.profile_id, item.operation): item
        for profile in report.profiles
        for item in profile.operation_summaries
    }


def compare_runtime_reports(
    *,
    before: McpRuntimeReport,
    after: McpRuntimeReport,
    policy: McpRuntimePolicy,
    accepted_surface_sha256: str,
) -> McpUpgradeComparison:
    findings: list[str] = []
    if before.mode != "release" or after.mode != "release":
        findings.append("mcp_upgrade_requires_release_reports")
    if before.policy_sha256 != policy.policy_sha256:
        findings.append("mcp_upgrade_before_policy_mismatch")
    if after.policy_sha256 != policy.policy_sha256:
        findings.append("mcp_upgrade_after_policy_mismatch")
    if before.baseline_sha256 != after.baseline_sha256:
        findings.append("mcp_upgrade_contract_baseline_changed")
    if not before.passed:
        findings.append("mcp_upgrade_before_report_failed")
    if not after.passed:
        findings.append("mcp_upgrade_after_report_failed")

    for report_name, report in (("before", before), ("after", after)):
        if any(
            profile.surface_sha256 != accepted_surface_sha256
            for profile in report.profiles
        ):
            findings.append(f"mcp_upgrade_{report_name}_surface_drift")

    before_items = _summary_map(before)
    after_items = _summary_map(after)
    if set(before_items) != set(after_items):
        findings.append("mcp_upgrade_operation_coverage_changed")

    comparisons: list[McpUpgradeOperationComparison] = []
    for key in sorted(set(before_items) & set(after_items)):
        old = before_items[key]
        new = after_items[key]
        absolute = new.p95_ms - old.p95_ms
        # 本地极快调用可能接近 0 ms；至少以 1 ms 作分母，避免噪声放大。
        relative = absolute / max(old.p95_ms, 1.0)
        operation_findings: list[str] = []
        # 同时超过绝对值和相对值才判定性能退化，减少本地抖动误报。
        if (
            absolute > policy.maximum_absolute_p95_regression_ms
            and relative > policy.maximum_relative_p95_regression
        ):
            operation_findings.append("mcp_upgrade_p95_regressed")
        if not new.passed:
            operation_findings.append("mcp_upgrade_operation_failed")
        comparisons.append(
            McpUpgradeOperationComparison(
                profile_id=key[0],
                operation=key[1],
                before_p95_ms=old.p95_ms,
                after_p95_ms=new.p95_ms,
                absolute_change_ms=absolute,
                relative_change=relative,
                passed=not operation_findings,
                finding_codes=operation_findings,
            )
        )

    if any(not item.passed for item in comparisons):
        findings.append("mcp_upgrade_operation_regression")

    payload = {
        "schema_version": "phase56-v1",
        "comparison_id": f"mcpupgrade_{uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "before_report_sha256": before.report_sha256,
        "after_report_sha256": after.report_sha256,
        "accepted_surface_sha256": accepted_surface_sha256,
        "passed": not findings,
        "operation_comparisons": comparisons,
        "finding_codes": sorted(set(findings)),
    }
    comparison = McpUpgradeComparison(
        **payload,
        comparison_sha256="0" * 64,
    )
    return comparison.model_copy(
        update={
            "comparison_sha256": upgrade_comparison_hash(comparison)
        }
    )
