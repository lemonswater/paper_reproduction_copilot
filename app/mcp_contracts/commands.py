from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import settings
from app.mcp_contracts.baseline import (
    atomic_write_json,
    atomic_write_text,
    build_candidate,
    load_baseline,
    load_candidate,
    promote_candidate,
    write_candidate,
)
from app.mcp_contracts.evaluator import evaluate_profiles
from app.mcp_contracts.profiles import load_client_profiles
from app.mcp_contracts.readiness import inspect_mcp_stack
from app.mcp_contracts.schemas import (
    McpClientProfile,
    McpContractCandidate,
    McpContractEvalReport,
    McpEvalMode,
    McpStackReadinessReport,
)
from app.mcp_contracts.snapshot import (
    build_catalog_only_server,
    observe_in_memory,
    observe_streamable_http,
)
from app.secrets.factory import build_secret_service
from app.secrets.schemas import SecretUse


def _profiles() -> list[McpClientProfile]:
    return load_client_profiles(
        settings.mcp_client_profiles_path,
        allowed_root=settings.allowed_root,
    )


def _report_path(path: Path) -> Path:
    """所有 Candidate/Eval 输出都必须留在 Phase 55 Report Root。"""

    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ValueError("MCP contract output cannot be a symlink")
    resolved = candidate.resolve()
    root = settings.mcp_contract_report_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError("MCP contract output is outside report root")
    return resolved


def _resolve_profile_token(profile: McpClientProfile) -> str:
    if profile.secret_name is None:
        raise ValueError("HTTP profile has no secret_name")
    material = build_secret_service().resolve_current(
        name=profile.secret_name,
        use=SecretUse.MCP_EXPORT_AUTH,
        actor="runtime:mcp-contract-eval",
    )
    return material.reveal()


async def _observe_candidate_profiles(
    *,
    include_http: bool,
) -> list:
    server = build_catalog_only_server()
    observations = []
    for profile in _profiles():
        if profile.transport == "in_memory":
            observations.append(
                await observe_in_memory(server, profile=profile)
            )
        elif include_http:
            observations.append(
                await observe_streamable_http(
                    profile=profile,
                    token=_resolve_profile_token(profile),
                    timeout_seconds=settings.mcp_contract_timeout_seconds,
                )
            )
    return observations


def generate_candidate(
    *,
    include_http: bool,
    output_path: Path | None,
) -> tuple[Path, McpContractCandidate]:
    observations = asyncio.run(
        _observe_candidate_profiles(include_http=include_http)
    )
    candidate = build_candidate(observations)
    selected_path = _report_path(output_path or (
        settings.mcp_contract_report_root
        / "candidates"
        / f"{candidate.candidate_id}.json"
    ))
    write_candidate(selected_path, candidate)
    return selected_path, candidate


def accept_candidate(
    *,
    candidate_path: Path,
    expected_surface_sha256: str,
    reviewed_by: str,
    reason: str,
    replace: bool,
    expected_current_baseline_sha256: str | None,
):
    candidate = load_candidate(_report_path(candidate_path))
    return promote_candidate(
        candidate=candidate,
        baseline_path=settings.mcp_contract_baseline_path,
        expected_surface_sha256=expected_surface_sha256,
        reviewed_by=reviewed_by,
        reason=reason,
        replace=replace,
        expected_current_baseline_sha256=(
            expected_current_baseline_sha256
        ),
    )


def _render_report(report: McpContractEvalReport) -> str:
    lines = [
        "# MCP Contract Evaluation",
        "",
        f"- Eval ID: `{report.eval_id}`",
        f"- Mode: `{report.mode}`",
        f"- Passed: `{report.passed}`",
        f"- Baseline: `{report.baseline_sha256}`",
        f"- Report: `{report.report_sha256}`",
        "",
        "## Client Profiles",
        "",
        "| Profile | Status | Protocol | Surface |",
        "|---|---|---|---|",
    ]
    for item in report.profile_results:
        lines.append(
            "| "
            f"`{item.profile_id}` | `{item.status}` | "
            f"`{item.protocol_version or '-'}` | "
            f"`{item.surface_sha256 or '-'}` |"
        )
        for finding in item.findings:
            lines.append(
                f"\n- `{item.profile_id}` `{finding.code}`: "
                f"{finding.summary}"
            )
    lines.append("")
    return "\n".join(lines)


def run_contract_eval(
    *,
    mode: McpEvalMode,
) -> tuple[Path, Path, McpContractEvalReport]:
    baseline = load_baseline(settings.mcp_contract_baseline_path)
    report = asyncio.run(
        evaluate_profiles(
            profiles=_profiles(),
            baseline=baseline,
            mode=mode,
            timeout_seconds=settings.mcp_contract_timeout_seconds,
            token_resolver=_resolve_profile_token,
        )
    )
    root = settings.mcp_contract_report_root / "evals" / report.eval_id
    json_path = root / "report.json"
    markdown_path = root / "report.md"
    atomic_write_json(json_path, report.model_dump(mode="json"))
    atomic_write_text(markdown_path, _render_report(report))
    return json_path, markdown_path, report


def stack_doctor(
    *,
    connect_gateway: bool,
) -> McpStackReadinessReport:
    return inspect_mcp_stack(connect_gateway=connect_gateway)
