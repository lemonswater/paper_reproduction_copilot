from langgraph.types import interrupt
from app.tools.action_tools import build_approval_record, compute_action_hash

def human_review_node(state: dict) -> dict:
    if not state.get("requires_approval"):
        return {"user_approval": "not_required"}

    pending_action = state.get("pending_action")
    if not pending_action:
        return {"user_approval": "missing_action"}

    action_hash = state.get("pending_action_hash") or compute_action_hash(pending_action)
    
    payload = {
        "message": "请确认是否允许执行该操作",
        "action": pending_action,
        "action_hash": action_hash,
        "allowed_respomses": ["approved", "rejected", "revise"]
    }

    response = interrupt(payload)

    if isinstance(response, dict):
        decision = response.get("decision", "rejected")
        feedback = response.get("feedback")
    else:
        decision = str(response)
        feedback = None
    
    approval_record = build_approval_record(
        action=pending_action,
        action_hash=action_hash,
        decision=decision,
        risk_level=pending_action.get("risk", {}).get("level", "unknown"),
        comment=feedback,
    )

    return {
        "user_approval": decision,
        "human_feedback": feedback,
        "approval_record": approval_record,
        "pending_action_hash": action_hash
    }
