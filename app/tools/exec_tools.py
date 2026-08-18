from __future__ import annotations

from typing import Any

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.execution.registry import build_execution_runner
from app.schemas import StageError
from app.tools.artifact_tools import register_existing_artifact
from app.tools.error_tools import build_stage_error

RESOURCE_END_REASONS = {
    "timeout",
    "cpu_limit",
    "memory_limit",
    "process_limit",
    "write_limit",
    "gpu_limit",
}

def _execution_failure(
    *,
    message: str,
    end_reason: str,
    profile_id: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "returncode": None,
        "end_reason": end_reason,
        "stdout": "",
        "stderr": message,
        "combined_output": message,
        "timeout": end_reason == "timeout",
        "cancelled": end_reason in {"cancelled", "interrupted"},
        "log_truncated": False,
        "execution_profile_id": profile_id,
        "execution_backend": None,
        "resource_usage": {},
    }


def run_action_safe(
    action: dict,
    *,
    state: dict,
    stage: str,
) -> dict[str, Any]:
    """
    校验 profile 指纹后，把 Action 交给受监管 Runner。

    run_dir 必须来自当前 Graph state，不能回退到 outputs/ 或 profile 的
    artifact_root。
    """

    profile_id = action.get("execution_profile_id")
    if not profile_id:
        return _execution_failure(
            message="缺少 execution_profile_id",
            end_reason="policy_denied",
        )

    run_dir = state.get("run_dir")
    if not run_dir:
        return _execution_failure(
            message="当前 state 缺少 run_dir",
            end_reason="supervisor_error",
            profile_id=profile_id,
        )

    try:
        profile = get_execution_profile(profile_id)
        current_fingerprint = (
            compute_execution_profile_fingerprint(profile)
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return _execution_failure(
            message=str(exc),
            end_reason="launch_error",
            profile_id=profile_id,
        )

    expected_fingerprint = action.get(
        "execution_profile_fingerprint"
    )
    if expected_fingerprint != current_fingerprint:
        return _execution_failure(
            message=(
                "操作创建后执行环境安全配置发生变化；"
                "请重新构建并审批该操作"
            ),
            end_reason="policy_denied",
            profile_id=profile_id,
        )

    runner = build_execution_runner(profile)

    # OCI 后端需要 WorkspaceBinding 构造容器 ownership label。
    runtime_context = None
    if profile.backend == "oci":
        raw_binding = state.get("workspace_binding")
        if not raw_binding:
            return _execution_failure(
                message="OCI 后端需要 workspace_binding",
                end_reason="launch_error",
                profile_id=profile_id,
            )
        from app.execution.base import (
            ExecutionRuntimeContext,
        )
        from app.workspace.schemas import (
            WorkspaceBinding,
        )
        runtime_context = ExecutionRuntimeContext(
            job_id=str(state.get("job_id", "")),
            run_id=str(state.get("run_id", "")),
            workspace_binding=WorkspaceBinding.model_validate(
                raw_binding
            ),
        )

    return runner.run(
        action,
        run_dir=str(run_dir),
        stage=stage,
        runtime_context=runtime_context,
    )

def register_execution_artifacts(
    *,
    state: dict,
    result: dict[str, Any],
    producer_node: str,
) -> list:
    """登记 Supervisor 已经完整关闭并 fsync 的执行文件。"""

    candidates = [
        (result.get("stdout_path"), "text/plain"),
        (result.get("stderr_path"), "text/plain"),
        (result.get("combined_log_path"), "text/plain"),
        (
            result.get("process_record_path"),
            "application/json",
        ),
    ]
    records = []
    seen: set[str] = set()
    for raw_path, media_type in candidates:
        if not raw_path or raw_path in seen:
            continue
        seen.add(raw_path)
        records.append(
            register_existing_artifact(
                state=state,
                path=raw_path,
                producer_node=producer_node,
                media_type=media_type,
            )
        )
    return records


def build_execution_stage_error(
    *,
    stage: str,
    result: dict[str, Any],
    log_path: str | None,
) -> tuple[StageError, str]:
    """把 Process Supervisor 事实映射到 Phase 15 StageError。"""

    reason = str(result.get("end_reason") or "supervisor_error")
    context = {
        "end_reason": reason,
        "returncode": result.get("returncode"),
        "execution_id": result.get("execution_id"),
        "process_record_path": result.get(
            "process_record_path"
        ),
        "log_path": log_path,
        "resource_usage": result.get("resource_usage", {}),
        "log_truncated": result.get("log_truncated", False),
    }

    if reason == "exited":
        return (
            build_stage_error(
                stage=stage,
                code="PAPER_PROGRAM_NONZERO_EXIT",
                category="paper_program",
                message=(
                    "论文程序返回非零状态："
                    f"{result.get('returncode')}"
                ),
                terminal=False,
                context=context,
            ),
            "failed",
        )

    if reason in RESOURCE_END_REASONS:
        return (
            build_stage_error(
                stage=stage,
                code="PAPER_PROGRAM_RESOURCE_LIMIT",
                category="paper_program",
                message=f"论文程序触发执行预算：{reason}",
                terminal=False,
                context=context,
            ),
            "failed",
        )

    if reason in {"cancelled", "interrupted"}:
        return (
            build_stage_error(
                stage=stage,
                code="EXECUTION_CANCELLED",
                category="user",
                message=f"执行已取消：{reason}",
                terminal=True,
                context=context,
            ),
            "cancelled",
        )

    if reason == "policy_denied":
        return (
            build_stage_error(
                stage=stage,
                code="EXECUTION_POLICY_DENIED",
                category="user",
                message=result.get("stderr") or "执行策略拒绝",
                terminal=True,
                context=context,
            ),
            "policy_blocked",
        )

    if reason == "launch_error":
        return (
            build_stage_error(
                stage=stage,
                code="EXECUTION_LAUNCH_ERROR",
                category="environment",
                message=result.get("stderr") or "子进程启动失败",
                terminal=True,
                context=context,
            ),
            "environment_blocked",
        )

    return (
        build_stage_error(
            stage=stage,
            code="EXECUTION_SUPERVISOR_ERROR",
            category="agent",
            message=(
                result.get("stderr")
                or f"Supervisor 异常结束：{reason}"
            ),
            terminal=True,
            context=context,
        ),
        "agent_failed",
    )
