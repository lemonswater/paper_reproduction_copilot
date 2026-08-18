from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata, util

from app.config import settings
from app.mcp_contracts.baseline import load_baseline
from app.mcp_contracts.profiles import load_client_profiles
from app.mcp_contracts.schemas import (
    McpStackComponent,
    McpStackReadinessReport,
)


def _sdk_component() -> McpStackComponent:
    if util.find_spec("mcp") is None:
        return McpStackComponent(
            name="sdk",
            status="not_ready",
            issues=["mcp_sdk_missing"],
        )
    try:
        version = metadata.version("mcp")
        major = int(version.split(".", 1)[0])
    except Exception as exc:  # noqa: BLE001
        return McpStackComponent(
            name="sdk",
            status="not_ready",
            issues=[f"mcp_sdk_invalid:{type(exc).__name__}"],
        )
    if major != 2:
        return McpStackComponent(
            name="sdk",
            status="not_ready",
            issues=["mcp_sdk_major_not_approved"],
        )
    return McpStackComponent(name="sdk", status="ready")


def _contract_component() -> McpStackComponent:
    issues: list[str] = []
    try:
        load_baseline(settings.mcp_contract_baseline_path)
    except Exception as exc:  # noqa: BLE001
        issues.append(f"baseline_invalid:{type(exc).__name__}")
    try:
        load_client_profiles(
            settings.mcp_client_profiles_path,
            allowed_root=settings.allowed_root,
        )
    except Exception as exc:  # noqa: BLE001
        issues.append(f"profiles_invalid:{type(exc).__name__}")
    return McpStackComponent(
        name="contracts",
        status="not_ready" if issues else "ready",
        issues=issues,
    )


def _gateway_component(*, connect: bool) -> McpStackComponent:
    if not settings.mcp_gateway_enabled:
        return McpStackComponent(name="gateway", status="disabled")

    from app.mcp_gateway.factory import inspect_mcp_gateway

    report = inspect_mcp_gateway(connect=connect)
    return McpStackComponent(
        name="gateway",
        status="ready" if report.ready else "not_ready",
        issues=list(report.issues),
    )


def _export_component() -> McpStackComponent:
    if not settings.mcp_export_enabled:
        return McpStackComponent(name="export", status="disabled")

    from app.mcp_export.factory import inspect_mcp_export

    report = inspect_mcp_export()
    return McpStackComponent(
        name="export",
        status="ready" if report.ready else "not_ready",
        issues=list(report.issues),
    )


def _runtime_component() -> McpStackComponent:
    """验证策略和最新 release Report；默认不发起 MCP 调用。"""

    if not settings.mcp_export_enabled:
        return McpStackComponent(name="runtime", status="disabled")

    from app.mcp_operations.policy import load_runtime_policy
    from app.mcp_operations.repository import load_runtime_report

    issues: list[str] = []
    try:
        policy = load_runtime_policy(
            settings.mcp_runtime_policy_path,
            allowed_root=settings.allowed_root,
        )
    except Exception as exc:  # noqa: BLE001
        return McpStackComponent(
            name="runtime",
            status="not_ready",
            issues=[f"runtime_policy_invalid:{type(exc).__name__}"],
        )

    try:
        candidates = sorted(
            settings.mcp_runtime_report_root.glob(
                "reports/mcpruntime_*/report.json"
            ),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
    except OSError as exc:
        return McpStackComponent(
            name="runtime",
            status="not_ready",
            issues=[f"runtime_report_scan_failed:{type(exc).__name__}"],
        )
    if not candidates:
        issues.append("runtime_release_report_missing")
    else:
        try:
            report = load_runtime_report(
                candidates[0],
                root=settings.mcp_runtime_report_root,
            )
            baseline = load_baseline(
                settings.mcp_contract_baseline_path
            )
            if report.mode != "release":
                issues.append("latest_runtime_report_not_release")
            if not report.passed:
                issues.append("latest_runtime_report_failed")
            if report.policy_sha256 != policy.policy_sha256:
                issues.append("latest_runtime_policy_stale")
            if report.baseline_sha256 != baseline.baseline_sha256:
                issues.append("latest_runtime_baseline_stale")
        except Exception as exc:  # noqa: BLE001
            issues.append(
                f"runtime_report_invalid:{type(exc).__name__}"
            )

    return McpStackComponent(
        name="runtime",
        status="not_ready" if issues else "ready",
        issues=issues,
    )


def inspect_mcp_stack(
    *,
    connect_gateway: bool = False,
) -> McpStackReadinessReport:
    """默认不联网；只有显式 connect_gateway 才检查 Phase 53 endpoint。"""

    components = [
        _sdk_component(),
        _contract_component(),
        _gateway_component(connect=connect_gateway),
        _export_component(),
        _runtime_component(),
    ]
    statuses = {item.status for item in components}
    if "not_ready" in statuses:
        overall = "not_ready"
    elif "degraded" in statuses:
        overall = "degraded"
    elif statuses == {"disabled"}:
        overall = "disabled"
    else:
        # Feature 可以关闭，但 SDK/Contract 仍可 ready。
        overall = "ready"

    return McpStackReadinessReport(
        status=overall,
        generated_at=datetime.now(timezone.utc).isoformat(),
        components=components,
    )
