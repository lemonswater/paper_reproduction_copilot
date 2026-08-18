from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from app.config import settings
from app.mcp_contracts.baseline import load_baseline
from app.mcp_contracts.profiles import load_client_profiles
from app.mcp_contracts.schemas import McpClientProfile
from app.mcp_export.factory import (
    build_mcp_export_runtime,
)
from app.mcp_export.server import build_mcp_export_server
from app.mcp_operations.errors import McpRuntimePolicyInvalid
from app.mcp_operations.policy import load_runtime_policy
from app.mcp_operations.probe import (
    McpProbeTarget,
    run_runtime_probe,
)
from app.mcp_operations.repository import (
    load_runtime_report,
    write_runtime_report,
    write_upgrade_comparison,
)
from app.mcp_operations.upgrade import compare_runtime_reports
from app.secrets.factory import build_secret_service
from app.secrets.schemas import SecretUse


ProbeMode = Literal["offline", "release"]


def _in_memory_target(
    *,
    profile: McpClientProfile,
    server: Any,
    timeout_seconds: float,
) -> McpProbeTarget:
    def connect():
        from mcp import Client

        return Client(
            server,
            mode=profile.mode,
            raise_exceptions=True,
            read_timeout_seconds=timeout_seconds,
        )

    return McpProbeTarget(profile=profile, connect=connect)


def _resolve_profile_token(profile: McpClientProfile) -> str:
    if profile.secret_name is None:
        raise McpRuntimePolicyInvalid(
            "HTTP Profile has no secret reference"
        )
    material = build_secret_service().resolve_current(
        name=profile.secret_name,
        use=SecretUse.MCP_EXPORT_AUTH,
        actor="runtime:mcp-runtime-probe",
    )
    return material.reveal()


@asynccontextmanager
async def _http_client_context(
    *,
    profile: McpClientProfile,
    token: str,
    timeout_seconds: float,
):
    if profile.endpoint is None:
        raise McpRuntimePolicyInvalid("HTTP Profile has no endpoint")

    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx2.Timeout(timeout_seconds),
        follow_redirects=False,
        trust_env=False,
    ) as http_client:
        transport = streamable_http_client(
            profile.endpoint,
            http_client=http_client,
        )
        async with Client(
            transport,
            mode=profile.mode,
            raise_exceptions=True,
            read_timeout_seconds=timeout_seconds,
        ) as client:
            yield client


def _http_target(
    *,
    profile: McpClientProfile,
    timeout_seconds: float,
) -> McpProbeTarget:
    # Secret 只进入闭包和短生命周期 HTTP Client，不写入 Target Schema。
    token = _resolve_profile_token(profile)

    def connect():
        return _http_client_context(
            profile=profile,
            token=token,
            timeout_seconds=timeout_seconds,
        )

    return McpProbeTarget(profile=profile, connect=connect)


def _build_targets(
    *,
    mode: ProbeMode,
) -> tuple[list[McpProbeTarget], Any, Any]:
    policy = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    profiles = load_client_profiles(
        settings.mcp_client_profiles_path,
        allowed_root=settings.allowed_root,
    )
    profile_by_id = {item.profile_id: item for item in profiles}
    required_ids = (
        policy.offline_profile_ids
        if mode == "offline"
        else policy.release_profile_ids
    )
    missing = sorted(set(required_ids) - set(profile_by_id))
    if missing:
        raise McpRuntimePolicyInvalid(
            "required MCP runtime Profile is missing"
        )

    # Offline 和 release 都验证 in-memory；release 额外验证真实 HTTP。
    runtime = build_mcp_export_runtime()
    server = build_mcp_export_server(
        runtime.service,
        telemetry=runtime.telemetry,
    )
    targets: list[McpProbeTarget] = []
    for profile_id in required_ids:
        profile = profile_by_id[profile_id]
        if mode == "offline" and profile.transport != "in_memory":
            raise McpRuntimePolicyInvalid(
                "offline runtime Profile must use in_memory transport"
            )
        if profile.transport == "in_memory":
            targets.append(
                _in_memory_target(
                    profile=profile,
                    server=server,
                    timeout_seconds=policy.request_timeout_seconds,
                )
            )
        elif mode == "release":
            targets.append(
                _http_target(
                    profile=profile,
                    timeout_seconds=policy.request_timeout_seconds,
                )
            )
    # runtime 必须活到 asyncio.run() 结束，故作为返回值保留强引用。
    return targets, policy, runtime


def run_runtime_evaluation(
    *,
    mode: ProbeMode,
    job_id: str,
):
    targets, policy, runtime = _build_targets(mode=mode)
    baseline = load_baseline(settings.mcp_contract_baseline_path)
    report = asyncio.run(
        run_runtime_probe(
            mode=mode,
            policy=policy,
            baseline=baseline,
            targets=targets,
            job_id=job_id,
        )
    )
    # 保留局部变量，明确 runtime 生命周期覆盖整个 Probe。
    _ = runtime
    json_path, markdown_path = write_runtime_report(
        root=settings.mcp_runtime_report_root,
        report=report,
    )
    return json_path, markdown_path, report


def compare_upgrade_reports(
    *,
    before_path: Path,
    after_path: Path,
):
    root = settings.mcp_runtime_report_root
    policy = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    baseline = load_baseline(settings.mcp_contract_baseline_path)
    before = load_runtime_report(before_path, root=root)
    after = load_runtime_report(after_path, root=root)
    comparison = compare_runtime_reports(
        before=before,
        after=after,
        policy=policy,
        accepted_surface_sha256=(
            baseline.accepted_surface_sha256
        ),
    )
    output_path = write_upgrade_comparison(
        root=root,
        comparison=comparison,
    )
    return output_path, comparison
