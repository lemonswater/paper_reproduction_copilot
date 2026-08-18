from __future__ import annotations

from pathlib import Path

from app.mcp_contracts.baseline import (
    atomic_write_json,
    atomic_write_text,
)
from app.mcp_operations.errors import McpRuntimeReportInvalid
from app.mcp_operations.identity import (
    runtime_report_hash,
    upgrade_comparison_hash,
)
from app.mcp_operations.schemas import (
    McpRuntimeReport,
    McpUpgradeComparison,
)


def _inside_root(path: Path, root: Path) -> Path:
    if path.is_symlink():
        raise McpRuntimeReportInvalid(
            "MCP runtime artifact must not be a symlink"
        )
    selected = path.expanduser().resolve()
    allowed = root.expanduser().resolve()
    if selected == allowed or allowed not in selected.parents:
        raise McpRuntimeReportInvalid(
            "MCP runtime artifact is outside report root"
        )
    return selected


def _render_runtime_report(report: McpRuntimeReport) -> str:
    lines = [
        "# MCP Runtime Evaluation",
        "",
        f"- Report: `{report.report_id}`",
        f"- Mode: `{report.mode}`",
        f"- Passed: `{report.passed}`",
        f"- Policy: `{report.policy_sha256}`",
        f"- Contract baseline: `{report.baseline_sha256}`",
        f"- Report SHA-256: `{report.report_sha256}`",
        "",
        "| Profile | Operation | Success | P95 ms | Passed |",
        "|---|---|---:|---:|---|",
    ]
    for profile in report.profiles:
        for item in profile.operation_summaries:
            lines.append(
                f"| `{profile.profile_id}` | `{item.operation}` | "
                f"{item.success_count}/{item.sample_count} | "
                f"{item.p95_ms:.2f} | `{item.passed}` |"
            )
    if report.finding_codes:
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- `{code}`" for code in report.finding_codes)
    lines.append("")
    return "\n".join(lines)


def write_runtime_report(
    *,
    root: Path,
    report: McpRuntimeReport,
) -> tuple[Path, Path]:
    if runtime_report_hash(report) != report.report_sha256:
        raise McpRuntimeReportInvalid("runtime report hash mismatch")
    report_root = root / "reports" / report.report_id
    json_path = _inside_root(report_root / "report.json", root)
    markdown_path = _inside_root(report_root / "report.md", root)
    atomic_write_json(json_path, report.model_dump(mode="json"))
    atomic_write_text(markdown_path, _render_runtime_report(report))
    return json_path, markdown_path


def load_runtime_report(
    path: Path,
    *,
    root: Path,
) -> McpRuntimeReport:
    selected = _inside_root(path, root)
    if not selected.is_file():
        raise McpRuntimeReportInvalid("runtime report does not exist")
    try:
        report = McpRuntimeReport.model_validate_json(
            selected.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise McpRuntimeReportInvalid(
            "runtime report is invalid"
        ) from exc
    if runtime_report_hash(report) != report.report_sha256:
        raise McpRuntimeReportInvalid("runtime report hash mismatch")
    return report


def write_upgrade_comparison(
    *,
    root: Path,
    comparison: McpUpgradeComparison,
) -> Path:
    if (
        upgrade_comparison_hash(comparison)
        != comparison.comparison_sha256
    ):
        raise McpRuntimeReportInvalid("upgrade comparison hash mismatch")
    path = _inside_root(
        root
        / "upgrades"
        / comparison.comparison_id
        / "comparison.json",
        root,
    )
    atomic_write_json(path, comparison.model_dump(mode="json"))
    return path
