from __future__ import annotations


from app.config import settings
from app.nodes.run_context_node import run_context_node
from app.tools.artifact_tools import write_text_artifact


def _new_run(task_id: str) -> dict:
    state = {
        "task_id": task_id,
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
    }
    state.update(run_context_node(state))
    return state


def test_two_runs_do_not_overwrite_same_artifact_name(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    run_a = _new_run("run-a")
    run_b = _new_run("run-b")

    path_a, record_a = write_text_artifact(
        state=run_a,
        relative_path="execution/execution.log",
        text="output from A",
        producer_node="executor",
    )
    path_b, record_b = write_text_artifact(
        state=run_b,
        relative_path="execution/execution.log",
        text="output from B",
        producer_node="executor",
    )

    assert run_a["run_id"] != run_b["run_id"]
    assert run_a["run_dir"] != run_b["run_dir"]
    assert path_a != path_b
    assert path_a.read_text(encoding="utf-8") == "output from A"
    assert path_b.read_text(encoding="utf-8") == "output from B"
    assert record_a.run_id == run_a["run_id"]
    assert record_b.run_id == run_b["run_id"]
    assert record_a.sha256 != record_b.sha256