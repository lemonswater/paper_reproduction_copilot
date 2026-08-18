from __future__ import annotations

import asyncio
import math
from collections.abc import (
    Awaitable,
    Callable,
)
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from pydantic import ValidationError

from app.mcp_contracts.identity import sha256_value
from app.mcp_contracts.schemas import (
    McpClientProfile,
    McpContractBaseline,
    McpRuntimeFingerprint,
)
from app.mcp_contracts.snapshot import observe_connected_client
from app.mcp_export.identity import validate_job_id
from app.mcp_operations.identity import runtime_report_hash
from app.mcp_operations.schemas import (
    McpInvocationSample,
    McpOperationKind,
    McpOperationStatus,
    McpOperationSummary,
    McpRuntimePolicy,
    McpRuntimeProfileResult,
    McpRuntimeReport,
)


ProbeMode = Literal["offline", "release"]


class _ProbeSchemaError(RuntimeError):
    pass


class _ProbeToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class McpProbeTarget:
    """一个 Profile 和创建其真实 Client Context 的工厂。"""

    profile: McpClientProfile
    connect: Callable[[], AbstractAsyncContextManager]


@dataclass(frozen=True)
class _Operation:
    name: str
    kind: McpOperationKind
    invoke: Callable[[Any, float], Awaitable[Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _p95(values: list[float]) -> float:
    """使用 nearest-rank；少量本地样本也能得到确定性结果。"""

    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _classify_exception(
    exc: BaseException,
) -> tuple[McpOperationStatus, str]:
    # 只匹配允许公开的稳定 code；绝不把 str(exc) 写入 Report。
    public_text = str(exc)
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "timeout", "MCP_RUNTIME_TIMEOUT"
    if "MCP_EXPORT_BUSY" in public_text:
        return "busy", "MCP_EXPORT_BUSY"
    if "MCP_EXPORT_TIMEOUT" in public_text:
        return "timeout", "MCP_EXPORT_TIMEOUT"
    if isinstance(exc, (ValidationError, _ProbeSchemaError)):
        return "schema_error", "MCP_RUNTIME_SCHEMA_ERROR"
    if isinstance(exc, _ProbeToolError):
        return "failed", "MCP_RUNTIME_TOOL_ERROR"

    module = type(exc).__module__
    if module.startswith(("httpx", "httpx2")):
        return "transport_error", "MCP_RUNTIME_TRANSPORT_ERROR"
    return "protocol_error", "MCP_RUNTIME_PROTOCOL_ERROR"


async def _call_tool(
    client: Any,
    *,
    name: str,
    arguments: dict[str, Any],
    timeout_seconds: float,
) -> Any:
    result = await asyncio.wait_for(
        client.call_tool(
            name,
            arguments,
            read_timeout_seconds=timeout_seconds,
        ),
        timeout=timeout_seconds + 0.25,
    )
    if result.is_error is True:
        raise _ProbeToolError("tool returned an MCP error")
    if result.structured_content is None:
        raise _ProbeSchemaError("tool omitted structured_content")
    return result.structured_content


async def _read_resource(
    client: Any,
    *,
    uri: str,
    timeout_seconds: float,
) -> Any:
    # Client.read_resource() 没有逐次 timeout 参数，因此再加外层硬 deadline。
    result = await asyncio.wait_for(
        client.read_resource(uri),
        timeout=timeout_seconds,
    )
    if not result.contents:
        raise _ProbeSchemaError("resource returned no content")
    return result.model_dump(mode="json")


def _operations(job_id: str) -> list[_Operation]:
    """固定六个只读操作；闭包只在本次 Probe 生命周期内持有 Job ID。"""

    return [
        _Operation(
            name="get_reproduction_status",
            kind="tool",
            invoke=lambda client, timeout: _call_tool(
                client,
                name="get_reproduction_status",
                arguments={"job_id": job_id},
                timeout_seconds=timeout,
            ),
        ),
        _Operation(
            name="list_reproduction_artifacts",
            kind="tool",
            invoke=lambda client, timeout: _call_tool(
                client,
                name="list_reproduction_artifacts",
                arguments={"job_id": job_id, "limit": 5},
                timeout_seconds=timeout,
            ),
        ),
        _Operation(
            name="read_reproduction_final_report",
            kind="tool",
            invoke=lambda client, timeout: _call_tool(
                client,
                name="read_reproduction_final_report",
                arguments={"job_id": job_id},
                timeout_seconds=timeout,
            ),
        ),
        _Operation(
            name="search_reproduction_evidence",
            kind="tool",
            invoke=lambda client, timeout: _call_tool(
                client,
                name="search_reproduction_evidence",
                # 固定探测语句不来自用户输入，也不会写入 Report。
                arguments={
                    "job_id": job_id,
                    "query": "reproduction status and final result",
                    "limit": 3,
                },
                timeout_seconds=timeout,
            ),
        ),
        _Operation(
            name="resource_job_status",
            kind="resource",
            invoke=lambda client, timeout: _read_resource(
                client,
                uri=f"repro://jobs/{job_id}/status",
                timeout_seconds=timeout,
            ),
        ),
        _Operation(
            name="resource_final_report",
            kind="resource",
            invoke=lambda client, timeout: _read_resource(
                client,
                uri=f"repro://jobs/{job_id}/final-report",
                timeout_seconds=timeout,
            ),
        ),
    ]


async def _sample_operation(
    *,
    client: Any,
    profile_id: str,
    operation: _Operation,
    sample_index: int,
    timeout_seconds: float,
) -> McpInvocationSample:
    started = perf_counter()
    try:
        output = await operation.invoke(client, timeout_seconds)
    except Exception as exc:
        status, error_code = _classify_exception(exc)
        return McpInvocationSample(
            profile_id=profile_id,
            operation=operation.name,
            kind=operation.kind,
            sample_index=sample_index,
            status=status,
            duration_ms=(perf_counter() - started) * 1000,
            error_code=error_code,
        )

    return McpInvocationSample(
        profile_id=profile_id,
        operation=operation.name,
        kind=operation.kind,
        sample_index=sample_index,
        status="succeeded",
        duration_ms=(perf_counter() - started) * 1000,
        output_sha256=sha256_value(output),
    )


def _connection_failure_samples(
    *,
    profile_id: str,
    operations: list[_Operation],
    sample_count: int,
    exc: BaseException,
) -> list[McpInvocationSample]:
    status, error_code = _classify_exception(exc)
    if status not in {"timeout", "transport_error"}:
        status = "transport_error"
        error_code = "MCP_RUNTIME_CONNECT_FAILED"
    return [
        McpInvocationSample(
            profile_id=profile_id,
            operation=operation.name,
            kind=operation.kind,
            sample_index=index,
            status=status,
            duration_ms=0.0,
            error_code=error_code,
        )
        for operation in operations
        for index in range(sample_count)
    ]


def _summarize_operation(
    *,
    profile_id: str,
    operation: _Operation,
    samples: list[McpInvocationSample],
    policy: McpRuntimePolicy,
) -> McpOperationSummary:
    selected = [
        item
        for item in samples
        if item.profile_id == profile_id
        and item.operation == operation.name
    ]
    if not selected:
        return McpOperationSummary(
            profile_id=profile_id,
            operation=operation.name,
            kind=operation.kind,
            sample_count=0,
            success_count=0,
            success_rate=0.0,
            p95_ms=0.0,
            passed=False,
            finding_codes=["mcp_operation_samples_missing"],
        )
    succeeded = sum(item.status == "succeeded" for item in selected)
    success_rate = succeeded / len(selected)
    p95_ms = _p95([item.duration_ms for item in selected])
    findings: list[str] = []
    if success_rate < policy.minimum_success_rate:
        findings.append("mcp_operation_success_rate_below_slo")
    if p95_ms > policy.maximum_p95_ms:
        findings.append("mcp_operation_p95_above_slo")
    for status in sorted({item.status for item in selected} - {"succeeded"}):
        findings.append(f"mcp_operation_{status}")
    return McpOperationSummary(
        profile_id=profile_id,
        operation=operation.name,
        kind=operation.kind,
        sample_count=len(selected),
        success_count=succeeded,
        success_rate=success_rate,
        p95_ms=p95_ms,
        passed=not findings,
        finding_codes=findings,
    )


def _profile_result(
    *,
    profile: McpClientProfile,
    runtime: McpRuntimeFingerprint | None,
    surface_sha256: str | None,
    baseline: McpContractBaseline,
    operations: list[_Operation],
    samples: list[McpInvocationSample],
    policy: McpRuntimePolicy,
    connection_failed: bool,
) -> McpRuntimeProfileResult:
    summaries = [
        _summarize_operation(
            profile_id=profile.profile_id,
            operation=operation,
            samples=samples,
            policy=policy,
        )
        for operation in operations
    ]
    findings: list[str] = []
    if connection_failed:
        findings.append("mcp_profile_connect_failed")
    if surface_sha256 != baseline.accepted_surface_sha256:
        findings.append("mcp_runtime_surface_drift")
    if runtime is None:
        findings.append("mcp_runtime_fingerprint_missing")
    else:
        if runtime.mcp_sdk_major not in policy.allowed_sdk_majors:
            findings.append("mcp_sdk_major_not_allowed")
        if runtime.protocol_version not in policy.allowed_protocol_versions:
            findings.append("mcp_protocol_version_not_allowed")
    if any(not item.passed for item in summaries):
        findings.append("mcp_profile_operation_slo_failed")

    return McpRuntimeProfileResult(
        profile_id=profile.profile_id,
        runtime=runtime,
        surface_sha256=surface_sha256,
        operation_summaries=summaries,
        passed=not findings,
        finding_codes=sorted(set(findings)),
    )


async def run_runtime_probe(
    *,
    mode: ProbeMode,
    policy: McpRuntimePolicy,
    baseline: McpContractBaseline,
    targets: list[McpProbeTarget],
    job_id: str,
) -> McpRuntimeReport:
    """顺序执行，避免 Probe 自己触发 Phase 54 调用速率限制。"""

    selected_job_id = validate_job_id(job_id)
    operations = _operations(selected_job_id)
    expected_operations = set(policy.required_operation_names)
    if {item.name for item in operations} != expected_operations:
        raise ValueError("probe operation registry does not match policy")

    required_profiles = (
        policy.offline_profile_ids
        if mode == "offline"
        else policy.release_profile_ids
    )
    target_by_id = {item.profile.profile_id: item for item in targets}
    samples: list[McpInvocationSample] = []
    profile_results: list[McpRuntimeProfileResult] = []
    global_findings: list[str] = []

    for profile_id in required_profiles:
        target = target_by_id.get(profile_id)
        if target is None:
            global_findings.append(f"missing_profile:{profile_id}")
            continue

        runtime: McpRuntimeFingerprint | None = None
        surface_sha256: str | None = None
        connection_failed = False
        profile_samples: list[McpInvocationSample] = []
        try:
            async with target.connect() as client:
                observation = await asyncio.wait_for(
                    observe_connected_client(
                        client,
                        profile=target.profile,
                    ),
                    timeout=policy.request_timeout_seconds,
                )
                runtime = observation.runtime
                surface_sha256 = observation.surface.surface_sha256

                for operation in operations:
                    for index in range(policy.samples_per_operation):
                        profile_samples.append(
                            await _sample_operation(
                                client=client,
                                profile_id=profile_id,
                                operation=operation,
                                sample_index=index,
                                timeout_seconds=(
                                    policy.request_timeout_seconds
                                ),
                            )
                        )
        except Exception as exc:
            connection_failed = True
            profile_samples = _connection_failure_samples(
                profile_id=profile_id,
                operations=operations,
                sample_count=policy.samples_per_operation,
                exc=exc,
            )

        samples.extend(profile_samples)
        profile_results.append(
            _profile_result(
                profile=target.profile,
                runtime=runtime,
                surface_sha256=surface_sha256,
                baseline=baseline,
                operations=operations,
                samples=profile_samples,
                policy=policy,
                connection_failed=connection_failed,
            )
        )

    if len(profile_results) != len(required_profiles):
        global_findings.append("mcp_required_profile_coverage_missing")
    if any(not item.passed for item in profile_results):
        global_findings.append("mcp_runtime_profile_failed")

    payload = {
        "schema_version": "phase56-v1",
        "report_id": f"mcpruntime_{uuid4().hex[:16]}",
        "mode": mode,
        "generated_at": utc_now(),
        "policy_sha256": policy.policy_sha256,
        "baseline_sha256": baseline.baseline_sha256,
        "passed": not global_findings,
        "profiles": profile_results,
        "samples": samples,
        "finding_codes": sorted(set(global_findings)),
    }
    report = McpRuntimeReport(
        **payload,
        report_sha256="0" * 64,
    )
    return report.model_copy(
        update={"report_sha256": runtime_report_hash(report)}
    )
