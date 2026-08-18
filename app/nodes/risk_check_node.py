from __future__ import annotations

from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.execution.profile_store import get_execution_profile
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result


def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return stage_error_result(
            state=state,
            stage="risk_check",
            code="PENDING_ACTION_REQUIRED",
            category="agent",
            message="风险检查前缺少 pending_action",
            extra_update={
                "requires_approval": False,
                "final_status": "invalid_action",
            },
        )

    profile_id = pending_action.get("execution_profile_id")
    if not profile_id:
        return stage_error_result(
            state=state,
            stage="risk_check",
            code="EXECUTION_PROFILE_REQUIRED",
            category="agent",
            message="Action 缺少 execution_profile_id",
            extra_update={"final_status": "invalid_action"},
        )

    profile = get_execution_profile(profile_id)
    decision = evaluate_action_capabilities(
        raw_action=pending_action,
        profile=profile,
    )

    report_path, report_record = write_json_artifact(
        state=state,
        relative_path="planning/capability_decision.json",
        payload=decision.model_dump(),
        producer_node="risk_check",
    )

    action_with_risk = {
        **pending_action,
        "risk": {
            "level": decision.risk_level,
            "reason": decision.reason,
            "blocked": not decision.allowed,
            "capability_decision_id": decision.decision_id,
        },
    }
    payload = {
        "pending_action": action_with_risk,
        "capability_decision": decision.model_dump(),
        "capability_report_path": str(report_path),
        "requires_approval": decision.requires_approval,
        **artifact_state_update(state, [report_record]),
    }

    if not decision.allowed:
        codes = ", ".join(
            violation.code
            for violation in decision.violations
        )
        return stage_error_result(
            state={**state, **payload},
            stage="risk_check",
            code="ACTION_CAPABILITY_POLICY_BLOCKED",
            category="user",
            message=f"Action 被能力策略拒绝：{codes}",
            extra_update={
                **payload,
                "requires_approval": False,
                "final_status": "policy_blocked",
            },
        )

    if not decision.requires_approval:
        payload.update(
            {
                "user_approval": "not_required",
                "error": None,
            }
        )

    return payload