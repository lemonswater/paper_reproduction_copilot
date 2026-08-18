from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from app.mcp_contracts.identity import report_hash
from app.mcp_contracts.schemas import (
    McpClientProfile,
    McpContractBaseline,
    McpContractEvalReport,
    McpContractFinding,
    McpEvalMode,
    McpProfileEvalResult,
    McpSurfaceObservation,
)
from app.mcp_contracts.snapshot import (
    build_catalog_only_server,
    observe_in_memory,
    observe_streamable_http,
)


def _finding(code: str, summary: str) -> McpContractFinding:
    return McpContractFinding(
        code=code,
        severity="error",
        summary=summary,
    )


def compare_observation(
    observation: McpSurfaceObservation,
    baseline: McpContractBaseline,
) -> list[McpContractFinding]:
    """完全确定性比较；不调用 LLM。"""

    findings: list[McpContractFinding] = []
    surface = observation.surface
    runtime = observation.runtime

    if surface.surface_sha256 != baseline.accepted_surface_sha256:
        findings.append(
            _finding("surface_hash_drift", "public MCP surface changed")
        )
    if surface.server_name != baseline.server_name:
        findings.append(
            _finding("server_name_drift", "server name changed")
        )
    if surface.server_version != baseline.server_version:
        findings.append(
            _finding("server_version_drift", "server version changed")
        )

    actual_tools = [item.name for item in surface.tools]
    if actual_tools != baseline.required_tool_names:
        findings.append(
            _finding("tool_catalog_drift", "tool catalog changed")
        )
    actual_templates = [
        item.uri_template for item in surface.resource_templates
    ]
    if actual_templates != baseline.required_resource_templates:
        findings.append(
            _finding(
                "resource_template_drift",
                "resource template catalog changed",
            )
        )

    if baseline.require_output_schema and any(
        item.output_schema is None for item in surface.tools
    ):
        findings.append(
            _finding(
                "output_schema_missing",
                "one or more tools have no output schema",
            )
        )
    if not baseline.allow_static_resources and surface.static_resource_uris:
        findings.append(
            _finding(
                "static_resource_exposed",
                "static resources are not approved",
            )
        )
    if not baseline.allow_prompts and surface.prompt_names:
        findings.append(
            _finding("prompt_exposed", "MCP prompts are not approved")
        )

    lowered_names = [item.lower() for item in actual_tools]
    if any(
        fragment.lower() in name
        for fragment in baseline.forbidden_name_fragments
        for name in lowered_names
    ):
        findings.append(
            _finding(
                "forbidden_tool_name",
                "tool catalog contains a mutation-like name",
            )
        )

    if runtime.mcp_sdk_major not in baseline.allowed_sdk_majors:
        findings.append(
            _finding("sdk_major_drift", "MCP SDK major is not approved")
        )
    if runtime.protocol_version not in baseline.allowed_protocol_versions:
        findings.append(
            _finding(
                "protocol_version_drift",
                "negotiated protocol version is not approved",
            )
        )
    return findings


async def evaluate_profiles(
    *,
    profiles: list[McpClientProfile],
    baseline: McpContractBaseline,
    mode: McpEvalMode,
    timeout_seconds: float,
    token_resolver: Callable[[McpClientProfile], str],
) -> McpContractEvalReport:
    server = build_catalog_only_server()
    results: list[McpProfileEvalResult] = []
    observed_hashes: set[str] = set()

    for profile in profiles:
        if mode == "offline" and profile.transport != "in_memory":
            results.append(
                McpProfileEvalResult(
                    profile_id=profile.profile_id,
                    status="skipped",
                    findings=[],
                )
            )
            continue

        try:
            if profile.transport == "in_memory":
                observation = await observe_in_memory(
                    server,
                    profile=profile,
                )
            else:
                # Resolver 返回短生命周期明文，不进入 Report。
                token = token_resolver(profile)
                observation = await observe_streamable_http(
                    profile=profile,
                    token=token,
                    timeout_seconds=timeout_seconds,
                )
            findings = compare_observation(observation, baseline)
            observed_hashes.add(observation.surface.surface_sha256)
            results.append(
                McpProfileEvalResult(
                    profile_id=profile.profile_id,
                    status="failed" if findings else "passed",
                    protocol_version=observation.runtime.protocol_version,
                    surface_sha256=observation.surface.surface_sha256,
                    findings=findings,
                )
            )
        except Exception as exc:  # noqa: BLE001
            # 只保留异常类型，不保存连接 body、Header 或 Token。
            results.append(
                McpProfileEvalResult(
                    profile_id=profile.profile_id,
                    status="failed",
                    findings=[
                        _finding(
                            "profile_observation_failed",
                            f"profile failed: {type(exc).__name__}",
                        )
                    ],
                )
            )

    if len(observed_hashes) > 1:
        for result in results:
            if result.status != "skipped":
                result.findings.append(
                    _finding(
                        "cross_profile_surface_mismatch",
                        "profiles observed different public surfaces",
                    )
                )
                result.status = "failed"

    required_ids = set(baseline.required_profile_ids)
    selected_results = [
        item
        for item in results
        if mode == "release"
        or item.profile_id in required_ids
        and item.status != "skipped"
    ]
    if mode == "release":
        result_by_id = {item.profile_id: item for item in results}
        required_ok = all(
            result_by_id.get(profile.profile_id) is not None
            and result_by_id[profile.profile_id].status == "passed"
            for profile in profiles
            if profile.required_for_release
        )
    else:
        required_ok = bool(selected_results) and all(
            item.status == "passed" for item in selected_results
        )

    payload = {
        "eval_id": f"mcpeval_{uuid4().hex[:16]}",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_sha256": baseline.baseline_sha256,
        "passed": required_ok,
        "profile_results": results,
    }
    report = McpContractEvalReport(
        **payload,
        report_sha256="0" * 64,
    )
    return report.model_copy(
        update={"report_sha256": report_hash(report)}
    )
