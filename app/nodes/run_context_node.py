from datetime import datetime, timezone

from app.tools.artifact_tools import build_run_id, create_run_layout


def run_context_node(state: dict) -> dict:
    existing_run_id = state.get("run_id")
    existing_run_dir = state.get("run_dir")
    existing_started_at = state.get("run_started_at")

    # 如果是从 checkpoint 恢复回来的，尽量复用原 run。
    if existing_run_id:
        layout = create_run_layout(existing_run_id)
        return {
            "run_id": existing_run_id,
            "run_dir": existing_run_dir or layout["run_root"],
            "run_started_at": existing_started_at
            or datetime.now(timezone.utc).isoformat(),
        }

    run_id = build_run_id(state.get("task_id"))
    layout = create_run_layout(run_id)

    return {
        "run_id": run_id,
        "run_dir": layout["run_root"],
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    }