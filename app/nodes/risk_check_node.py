from app.tools.safe_shell_tools import assess_action_risk

def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "requires_approval": False,
            "pending_action": None,
            "pending_action_bash" : None
        }
    
    action_type = pending_action.get("action_type")
    if action_type == "run_command":
        risk = assess_action_risk(pending_action)
        pending_action["risk"] = {
            "level": risk.risk_level,
            "reason": risk.reason,
            "blocked": risk.blocked
        }

        if risk.blocked:
            return {
                "pending_action": pending_action,
                "pending_action_hash": state.get("pending_action_hash"),
                "requires_approval": False,
                "final_status": "blocked",
                "error": risk.reason,
            }

        if risk.risk_level == "low":
            return {
                "pending_action": pending_action,
                "pending_action_hash": state.get("pending_action_hash"),
                "requires_approval": False,
                "user_approval": "not_required",
                "error": None,
            }

        return {
            "pending_action": pending_action,
            "pending_action_hash": state.get("pending_action_hash"),
            "requires_approval": True,
            "error": None,
        }
    
    if action_type in {"modify_config", "write_repo_file"}:
        pending_action["risk"] = {
            "level": "high",
            "reason": "action modifies user repository",
            "blocked": False,
        }
        return {
            "pending_action": pending_action,
            "pending_action_hash": state.get("pending_action_hash"),
            "requires_approval": True,
        }
    pending_action["risk"] = {
        "level": "medium",
        "reason": "unknown action type",
        "blocked": False,
    }
    return {
        "pending_action": pending_action,
        "pending_action_hash": state.get("pending_action_hash"),
        "requires_approval": True,
    }