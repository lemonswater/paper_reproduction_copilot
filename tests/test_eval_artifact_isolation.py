from __future__ import annotations

from pathlib import Path

from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)


def test_case_observations_use_distinct_run_paths(
    run_state: dict,
) -> None:
    state = dict(run_state)
    paths = []
    for case_id in ["case_a", "case_b"]:
        path, record = write_json_artifact(
            state=state,
            relative_path=(
                f"traces/eval_cases/{case_id}/"
                "observation.json"
            ),
            payload={"case_id": case_id},
            producer_node="agent_eval",
        )
        state.update(artifact_state_update(state, [record]))
        paths.append(path)

    run_dir = Path(state["run_dir"])
    assert paths[0] != paths[1]
    assert all(
        path.is_relative_to(run_dir)
        for path in paths
    )
    assert len(state["artifact_records"]) >= 3
