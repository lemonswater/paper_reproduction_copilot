from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.nodes.preflight_check_node import preflight_check_node
from app.schemas import PreflightReport


def _probe_result(run_state) -> dict:
    attempt = (
        Path(run_state["run_dir"])
        / "execution"
        / "attempts"
        / "probe-test"
    )
    attempt.mkdir(parents=True)
    paths = {
        "stdout_path": attempt / "stdout.log",
        "stderr_path": attempt / "stderr.log",
        "combined_log_path": attempt / "combined.log",
        "process_record_path": attempt / "process_record.json",
    }
    for path in paths.values():
        path.write_text("probe\n", encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def test_preflight_report_is_written_to_current_run(run_state) -> None:
    report = PreflightReport(
        action_id="action_demo",
        action_hash="hash_demo",
        ready_to_execute=True,
        summary="preflight passed",
        items=[],
        blocking_items=[],
        execution_enforcement_mode="best_effort",
        process_group_supported=True,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    probe = _probe_result(run_state)
    state = {
        **run_state,
        "repo_path": "/repo",
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py"],
            "cwd": "/repo",
        },
        "pending_action_hash": "hash_demo",
        "requires_approval": False,
    }

    with patch(
        "app.nodes.preflight_check_node.build_preflight_report",
        return_value=(report, [probe]),
    ) as mocked_build:
        result = preflight_check_node(state)

    mocked_build.assert_called_once_with(
        state["pending_action"],
        repo_path=state["repo_path"],
        action_hash="hash_demo",
        run_dir=run_state["run_dir"],
    )
    report_path = Path(run_state["run_dir"]) / "planning" / "preflight_report.json"
    markdown_path = Path(run_state["run_dir"]) / "planning" / "preflight_report.md"
    assert result["preflight_passed"] is True
    assert result["preflight_report_path"] == str(report_path)
    assert report_path.exists()
    assert markdown_path.exists()
    produced = {
        record["relative_path"]
        for record in result["artifact_records"]
        if record["producer_node"] == "preflight_check"
    }
    assert "planning/preflight_report.json" in produced
    assert "planning/preflight_report.md" in produced
    assert any(path.endswith("process_record.json") for path in produced)


def test_preflight_requires_run_dir() -> None:
    result = preflight_check_node(
        {"pending_action": {"action_type": "run_command"}}
    )

    assert result["preflight_passed"] is False
    assert result["final_status"] == "agent_failed"
