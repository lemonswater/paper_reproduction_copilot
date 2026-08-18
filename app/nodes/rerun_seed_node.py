# app/nodes/rerun_seed_node.py
from __future__ import annotations

from app.schemas import RunCommand
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)


def rerun_seed_node(state: dict) -> dict:
    """普通 Job 是 no-op；派生 Job 用可信种子覆盖 LLM 候选命令。"""

    raw_seed = state.get("rerun_seed")
    if raw_seed is None:
        return {}
    if not isinstance(raw_seed, dict):
        raise ValueError("rerun_seed 必须是 object")

    command = RunCommand.model_validate(raw_seed.get("run_command"))
    payload = {
        "proposal_id": raw_seed.get("proposal_id"),
        "proposal_hash": raw_seed.get("proposal_hash"),
        "source": raw_seed.get("source"),
        "template_hash": raw_seed.get("template_hash"),
        "run_command": command.model_dump(mode="json"),
    }
    path, record = write_json_artifact(
        state=state,
        relative_path="planning/rerun_seed.json",
        payload=payload,
        producer_node="rerun_seed",
    )

    # 所有依赖旧命令或旧 action 的状态都显式清空。
    return {
        "run_commands": [command.model_dump(mode="json")],
        "edited_run_commands": [],
        "selected_run_command_index": None,
        "command_selection_record": None,
        "pending_action": None,
        "pending_action_hash": None,
        "requires_approval": False,
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,
        "preflight_report": None,
        "preflight_passed": False,
        "rerun_seed_path": str(path),
        **artifact_state_update(state, [record]),
    }
