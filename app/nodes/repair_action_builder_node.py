from app.config import settings
from app.tools.repair_tools import (
    apply_command_repair_to_state,
    validate_bounded_repair_command,
)


def repair_action_builder_node(state: dict) -> dict:
    proposal = state.get("repair_proposal")
    if not proposal:
        return {
            "final_status": "no_repair_proposal",
            "error": "repair_proposal is missing",
        }

    attempts = int(state.get("repair_attempt_count", 0))
    if attempts >= settings.max_repair_attempts:
        return {
            "final_status": "repair_limit_reached",
            "error": f"max repair attempts reached: {settings.max_repair_attempts}",
        }

    kind = proposal.get("kind")
    repaired_command = (proposal.get("repaired_command") or "").strip()

    if kind != "edit_command":
        return {
            "final_status": "repair_proposal_only",
            "last_action_result": {
                "status": "repair_proposal_only",
                "proposal_kind": kind,
            },
        }

    ok, reason = validate_bounded_repair_command(repaired_command)
    if not ok:
        return {
            "final_status": "repair_out_of_bounds",
            "error": reason,
            "last_action_result": {
                "status": "repair_out_of_bounds",
                "proposal_kind": kind,
                "repaired_command": repaired_command,
            },
        }

    try:
        updated_action = apply_command_repair_to_state(state, repaired_command)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "repair_action_invalid",
            "error": str(exc),
            "last_action_result": {
                "status": "repair_action_invalid",
                "proposal_kind": kind,
                "repaired_command": repaired_command,
            },
        }

    history_entry = {
        "attempt": attempts + 1,
        "proposal_id": proposal.get("proposal_id"),
        "kind": kind,
        "repaired_command": repaired_command,
        "summary": proposal.get("summary"),
    }

    return {
        **updated_action,
        "repair_attempt_count": attempts + 1,
        "repair_history": [
            *state.get("repair_history", []),
            history_entry,
        ],

        # 新动作要重新走完整安全链。
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,

        # 旧 preflight / smoke / debug 结果已经过期，必须清空。
        "preflight_report": None,
        "preflight_passed": False,
        "preflight_report_path": None,
        "smoke_test_report": None,
        "smoke_test_status": None,
        "smoke_test_passed": False,
        "smoke_test_log_path": None,
        "debug_report": None,
        "log_path": None,
        "execution_result": {},
        "execution_log_path": None,
        "active_execution_mode": None,
        "final_status": None,
        "error": None,
    }
