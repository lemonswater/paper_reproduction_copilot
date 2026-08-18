from __future__ import annotations

from pydantic import ValidationError

from app.authority.evidence import (
    build_execution_verification,
)
from app.authority.schemas import ExecutionEvidence
from app.schemas import (
    ApprovalRecord,
    ExecutableAction,
    ExecutionResult,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import (
    persist_stage_errors,
    stage_error_result,
)
from app.tools.exec_tools import build_execution_stage_error


def _invalid_verification_input(
    state: dict,
    message: str,
) -> dict:
    return stage_error_result(
        state=state,
        stage="execution_verifier",
        code="EXECUTION_EVIDENCE_INVALID",
        category="agent",
        message=message,
        extra_update={
            "execution_verification": None,
            "execution_verification_hash": None,
            "final_status": "agent_failed",
        },
    )


def execution_verifier_node(state: dict) -> dict:
    """只读取既有执行事实，不调用 Runner，也不修改 Action。"""

    try:
        action = ExecutableAction.model_validate(
            state.get("pending_action")
        )
        result = ExecutionResult.model_validate(
            state.get("execution_result")
        )
        evidence = ExecutionEvidence.model_validate(
            state.get("execution_evidence")
        )
        decision = str(state.get("user_approval") or "")
        approval = (
            ApprovalRecord.model_validate(
                state.get("approval_record")
            )
            if decision == "approved"
            else None
        )
    except ValidationError as exc:
        return _invalid_verification_input(
            state,
            f"执行验证输入不完整或无效：{exc}",
        )

    verification = build_execution_verification(
        action=action,
        result=result,
        evidence=evidence,
        decision=decision,
        approval=approval,
    )

    _, record = write_json_artifact(
        state=state,
        relative_path=(
            "execution/execution_verification.json"
        ),
        payload=verification.model_dump(),
        producer_node="execution_verifier",
    )

    base_update = {
        "execution_verification": verification.model_dump(),
        "execution_verification_hash": (
            verification.verification_sha256
        ),
        "final_status": verification.projected_final_status,
        "last_action_result": {
            **dict(state.get("last_action_result") or {}),
            "status": verification.projected_final_status,
            "verification_sha256": (
                verification.verification_sha256
            ),
            "verification_scope": verification.claim_scope,
        },
        **artifact_state_update(state, [record]),
    }

    if verification.verdict == "verified":
        return {
            **base_update,
            "error": None,
        }

    if verification.verdict == "inconclusive":
        return stage_error_result(
            state={**state, **base_update},
            stage="execution_verifier",
            code="EXECUTION_VERIFICATION_INCONCLUSIVE",
            category="agent",
            message=verification.summary,
            extra_update=base_update,
        )

    # Evidence 完整但执行没有成功时，复用 Phase 15 已有错误分类；
    # 分类发生在 Verifier，而不是刚启动进程的 Executor。
    error, final_status = build_execution_stage_error(
        stage="execution_verifier",
        result=result.model_dump(),
        log_path=evidence.combined_log_path,
    )
    working_state = {
        **state,
        **base_update,
    }
    error_update = persist_stage_errors(
        state=working_state,
        new_errors=[error],
    )
    return {
        **base_update,
        **error_update,
        # persist_stage_errors 对 terminal error 会写通用状态；这里恢复
        # Phase 15 对具体 end_reason 的精确投影。
        "final_status": final_status,
        "log_path": (
            evidence.combined_log_path
            or state.get("log_path")
        ),
        "last_action_result": {
            **base_update["last_action_result"],
            "status": final_status,
        },
    }
