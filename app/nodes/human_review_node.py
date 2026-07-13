from langgraph.types import interrupt

def human_review_node(state: dict) -> dict:
    if not state.get("requires_approval"):
        return {"user_approval": "not_required"}

    pending_action = state.get("pending_action")
    if not pending_action:
        return {"user_approval": "missing_action"}
    
    payload = {
        "message": "请确认是否允许执行该操作",
        "action": pending_action,
        "allowed_respomses": ["approved", "rejected", "revise"]
    }

    response = interrupt(payload)

    if isinstance(response, dict):
        decision = response.get("decision", "rejected")
        feedback = response.get("feedback")
    else:
        decision = str(response)
        feedback = None
    
    return {
        "user_approval": decision,
        "human_feedback": feedback
    }
