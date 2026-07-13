from app.tools.safe_shell_tools import assess_command_risk

def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "requires_approval": False,
            "pending_action": None
        }
    
    action_type = pending_action.get("type")
    if action_type == "run_command":
        risk = assess_command_risk(pending_action["command"])
        pending_action["risk"] = {
            "level": risk.risk_level,
            "reason": risk.reason,
            "blocked": risk.blocked
        }
        return {
            "pending_action": pending_action,
            "requires_approval": not risk.blocked,
            "error": risk.reason if risk.blocked else None,
        }
    
    if action_type in {"modify_config", "write_repo_file"}:
        pending_action["risk"] = {
            "level": "high",
            "reason": "action modifies user repository",
            "blocked": False,
        }
        return {
            "pending_action": pending_action,
            "requires_approval": True,
        }
    pending_action["risk"] = {
        "level": "medium",
        "reason": "unknown action type",
        "blocked": False,
    }
    return {
        "pending_action": pending_action,
        "requires_approval": True,
    }