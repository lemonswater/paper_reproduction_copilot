from app.config import settings
from app.tools.action_tools import compute_action_hash
from app.tools.exec_tools import run_action_safe

def executor_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {"final_status": "no_pending_action"}

    decision = state.get("user_approval")

    if decision == "rejected":
        return {
            "final_status": "rejected",
            "last_action_result": {
                "status": "rejected",
                "pending_action": pending_action
            }
        }

    if decision == "revise":
        return {
            "final_status": "revise_requested",
            "last_action_result": {
                "status": "revise_requested",
                "pending_action": pending_action,
                "human_feedback": state.get("human_feedback"),
            },
        }

    if decision not in {"approved", "not_required"}:
        return {
            "final_status": "not_executed",
            "last_action_result": {
                "status": "not_executed",
                "pending_action": pending_action,
                "reason": f"unsupported approval status: {decision}",
            },
        }

    action_type = pending_action.get("action_type")
    if action_type != "run_command":
        return {
            "final_status": "unsupported_action",
            "last_action_result": {
                "status": "unsupported_action",
                "pending_action": pending_action,
            },
            "error": f"unsupported action type: {action_type}",
        }

    current_action_hash = compute_action_hash(pending_action)

    if decision == "approved":
        approval_record = state.get("approval_record")
        if not approval_record:
            return {
                "final_status": "missing_approval_record",
                "last_action_result": {
                    "status": "missing_approval_record",
                    "pending_action": pending_action,
                },
            }
        
        approved_hash = approval_record.get("action_hash")
        if approved_hash != current_action_hash:
            return {
                "final_status": "stale_approval",
                "last_action_result": {
                    "status": "stale_approval",
                    "pending_action": pending_action,
                    "approved_hash": approved_hash,
                    "current_hash": current_action_hash,
                },
                "error": "approval record does not match current action",
            }
            
    result = run_action_safe(pending_action)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.output_dir / "execution.log"
    log_path.write_text(result["combined_output"], encoding="utf-8")
    final_status = "succeeded" if result["ok"] else "failed"

    payload = {
        "active_execution_mode": "full",
        "execution_result": result,
        "execution_log_path": str(log_path),
        "last_action_result": {
            "status": final_status,
            "pending_action": pending_action,
            "returncode": result["returncode"],
        },
        "final_status": final_status,
        "output_files": [
            *state.get("output_files", []),
            str(log_path),
        ],
    }

    if final_status == "failed":
        payload["log_path"] = str(log_path)

    return payload