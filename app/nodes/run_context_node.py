from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.artifact_tools import (
    artifact_state_update,
    build_run_id,
    create_run_layout,
    write_json_artifact,
)


def run_context_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    为新 run 创建目录；checkpoint resume 时复用原 run。

    run_request 只保存任务元数据，不保存 API Key 或完整 Prompt。
    """

    existing_run_id = state.get("run_id")
    existing_run_dir = state.get("run_dir")
    existing_started_at = state.get("run_started_at")

    run_id = existing_run_id or build_run_id(state.get("task_id"))
    layout = create_run_layout(
        run_id,
        run_root_override=(
            existing_run_dir if existing_run_dir else None
        ),
    )
    expected_run_dir = Path(layout["run_root"]).resolve()
    if (
        existing_run_dir
        and Path(existing_run_dir).resolve() != expected_run_dir
    ):
        raise ValueError(
            "checkpoint 中的 run_id 与 run_dir 不匹配"
        )
    run_dir = str(expected_run_dir)
    run_started_at = (
        existing_started_at
        or datetime.now(timezone.utc).isoformat()
    )

    context_state = {
        **state,
        "run_id": run_id,
        "run_dir": run_dir,
        "run_started_at": run_started_at,
    }

    request_payload = {
        "job_id": state.get("job_id"),
        "thread_id": state.get("thread_id"),
        "run_id": run_id,
        "task_id": state.get("task_id"),
        "paper_path": state.get("paper_path"),
        "repo_path": state.get("repo_path"),
        "log_path": state.get("log_path"),
        "experiment_goal": state.get("experiment_goal"),
        "execution_profile_id": state.get("execution_profile_id"),
        "run_started_at": run_started_at,
    }

    request_path, request_record = write_json_artifact(
        state=context_state,
        relative_path="inputs/run_request.json",
        payload=request_payload,
        producer_node="run_context",
    )

    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "run_started_at": run_started_at,
        "stage_errors": list(state.get("stage_errors", [])),
        "artifact_records": list(
            state.get("artifact_records", [])
        ),
        **artifact_state_update(
            context_state,
            [request_record],
        ),
    }