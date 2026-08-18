from __future__ import annotations

from app.mcp_contracts.identity import sha256_value
from app.mcp_operations.schemas import (
    McpRuntimePolicy,
    McpRuntimeReport,
    McpUpgradeComparison,
)


def policy_hash(policy: McpRuntimePolicy) -> str:
    payload = policy.model_dump(
        mode="json",
        exclude={"policy_sha256"},
    )
    return sha256_value(payload)


def runtime_report_hash(report: McpRuntimeReport) -> str:
    payload = report.model_dump(
        mode="json",
        exclude={"report_sha256"},
    )
    return sha256_value(payload)


def upgrade_comparison_hash(
    comparison: McpUpgradeComparison,
) -> str:
    payload = comparison.model_dump(
        mode="json",
        exclude={"comparison_sha256"},
    )
    return sha256_value(payload)
