from app.config import settings
from app.execution.profile_store import compute_execution_profile_fingerprint, get_execution_profile
from app.tools.action_tools import build_run_action_from_command, compute_action_hash


def action_builder_node(state: dict) -> dict:
    existing_action = state.get("pending_action")
    if existing_action:
        return {
            "pending_action": existing_action,
            "pending_action_hash": state.get("pending_action_hash")
            or compute_action_hash(existing_action)
        }

    effective_run_commands = state.get("edited_run_commands") or state.get("run_commands", [])

    if not effective_run_commands:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "no_action"
        }
    
    selected_index = state.get("selected_run_command_index", 0)
    if selected_index < 0 or selected_index >= len(effective_run_commands):
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "invalid_action",
            "error": f"selected_run_command_index out of range: {selected_index}",
        }

    selected_command = effective_run_commands[selected_index]
    profile_id = (
        state.get("execution_profile_id")
        or settings.default_execution_profile
    )

    try:
        profile = get_execution_profile(profile_id)
        profile_fingerprint = compute_execution_profile_fingerprint(profile)

        # selected command 中的 cwd 仍然优先；如果模型没有给出，
        # 使用 profile.workspace_root，而不是 Agent 项目目录。
        cwd = selected_command.get("cwd") or profile.workspace_root

        action = build_run_action_from_command(
            command=selected_command["command"],
            cwd=cwd,
            source=selected_command.get("source", "inferred"),
            reason=selected_command.get("reason", "from experiment plan"),
            execution_profile_id=profile.profile_id,
            execution_profile_fingerprint=profile_fingerprint,
            timeout_seconds=300,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "invalid_action",
            "error": str(exc),
        }

    action_hash = compute_action_hash(action)

    return {
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
    }