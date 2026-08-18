from __future__ import annotations

from pydantic import ValidationError

from app.authority.evidence import build_execution_evidence
from app.schemas import (
    ExecutableAction,
    ExecutionResult,
)
from app.tools.action_tools import compute_action_hash
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.exec_tools import (
    register_execution_artifacts,
    run_action_safe,
)


def _run_approved_action(
    *,
    state: dict,
    pending_action: ExecutableAction,
) -> dict:
    """Executor 运行已批准 Action，并只返回 Process 事实和 Evidence。"""

    raw_result = run_action_safe(
        pending_action.model_dump(),
        state=state,
        stage="executor",
    )

    try:
        result = ExecutionResult.model_validate(raw_result)
    except ValidationError as exc:
        return stage_error_result(
            state=state,
            stage="executor",
            code="EXECUTION_RESULT_INVALID",
            category="agent",
            message=f"Runner 返回无效 ExecutionResult：{exc}",
            extra_update={
                "final_status": "agent_failed",
            },
        )

    process_records = register_execution_artifacts(
        state=state,
        result=result.model_dump(),
        producer_node="executor",
    )
    evidence = build_execution_evidence(
        action=pending_action,
        result=result,
        artifact_records=process_records,
    )

    # Evidence 自身也成为 Run-native Artifact。Evidence 中的 artifact_ids
    # 只绑定先前的进程文件，避免产生"Evidence 引用自身"的循环身份。
    _, evidence_record = write_json_artifact(
        state=state,
        relative_path=(
            "execution/execution_evidence.json"
        ),
        payload=evidence.model_dump(),
        producer_node="executor",
    )
    all_records = [*process_records, evidence_record]

    log_path = result.combined_log_path
    update = {
        "active_execution_mode": "full",
        "active_execution_id": result.execution_id,
        "active_process_record_path": (
            result.process_record_path
        ),
        "execution_end_reason": result.end_reason,
        "execution_resource_usage": (
            result.resource_usage.model_dump()
        ),
        "cancellation_requested": result.cancelled,
        "cancellation_reason": result.cancellation_reason,
        "execution_result": result.model_dump(),
        "execution_evidence": evidence.model_dump(),
        "execution_log_path": log_path,
        "last_action_result": {
            # 这里故意不写 succeeded/failed。Executor 只声明证据已记录。
            "status": "evidence_recorded",
            "pending_action": pending_action.model_dump(),
            "returncode": result.returncode,
            "end_reason": result.end_reason,
            "execution_id": result.execution_id,
            "evidence_sha256": evidence.evidence_sha256,
        },
        **artifact_state_update(state, all_records),
    }

    # 非成功结果先提供日志入口，真正错误类别由 Verifier 根据证据投影。
    if not result.ok and log_path:
        update["log_path"] = log_path

    return update


def executor_node(state: dict) -> dict:
    raw_action = state.get("pending_action")
    if not raw_action:
        return stage_error_result(
            state=state,
            stage="executor",
            code="PENDING_ACTION_REQUIRED",
            category="agent",
            message="执行前缺少 pending_action",
            extra_update={"final_status": "no_pending_action"},
        )

    try:
        pending_action = ExecutableAction.model_validate(raw_action)
    except ValidationError as exc:
        return stage_error_result(
            state=state,
            stage="executor",
            code="PENDING_ACTION_INVALID",
            category="agent",
            message=f"pending_action 无效：{exc}",
            extra_update={"final_status": "invalid_action"},
        )

    decision = state.get("user_approval")

    # 正常 Graph 不会把 rejected/revise 送入 Executor；这里保留 fail-closed
    # 兼容，防止直接调用节点时意外运行命令。
    if decision == "rejected":
        return {
            "final_status": "rejected",
            "last_action_result": {
                "status": "rejected",
                "pending_action": pending_action.model_dump(),
            },
        }

    if decision == "revise":
        return {
            "final_status": "revise_requested",
            "last_action_result": {
                "status": "revise_requested",
                "pending_action": pending_action.model_dump(),
                "human_feedback": state.get("human_feedback"),
            },
        }

    if decision not in {"approved", "not_required"}:
        return stage_error_result(
            state=state,
            stage="executor",
            code="EXECUTION_NOT_APPROVED",
            category="user",
            message=f"不支持的审批状态：{decision}",
            extra_update={
                "final_status": "not_executed",
                "last_action_result": {
                    "status": "not_executed",
                    "pending_action": pending_action.model_dump(),
                },
            },
        )

    if pending_action.action_type != "run_command":
        return stage_error_result(
            state=state,
            stage="executor",
            code="UNSUPPORTED_ACTION_TYPE",
            category="agent",
            message=(
                "不支持的操作类型："
                f"{pending_action.action_type}"
            ),
            extra_update={
                "final_status": "unsupported_action",
            },
        )

    current_action_hash = compute_action_hash(
        pending_action.model_dump()
    )

    if decision == "approved":
        approval_record = state.get("approval_record")
        if not approval_record:
            return stage_error_result(
                state=state,
                stage="executor",
                code="APPROVAL_RECORD_MISSING",
                category="agent",
                message="approved action 缺少 approval_record",
                extra_update={
                    "final_status": "missing_approval_record",
                },
            )

        approved_hash = approval_record.get("action_hash")
        if approved_hash != current_action_hash:
            return stage_error_result(
                state=state,
                stage="executor",
                code="STALE_ACTION_APPROVAL",
                category="user",
                message="审批记录与当前操作不匹配",
                extra_update={
                    "final_status": "stale_approval",
                    "last_action_result": {
                        "status": "stale_approval",
                        "pending_action": pending_action.model_dump(),
                        "approved_hash": approved_hash,
                        "current_hash": current_action_hash,
                    },
                },
            )

    return _run_approved_action(
        state=state,
        pending_action=pending_action,
    )
