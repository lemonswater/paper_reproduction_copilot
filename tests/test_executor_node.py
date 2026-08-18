from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.nodes.executor_node import executor_node
from app.schemas import ExecutableAction
from app.tools.action_tools import compute_action_hash
from app.tools.exec_tools import build_execution_stage_error


def _build_pending_action() -> dict:
    return {
        "action_id": "action_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/tmp/demo-repo",
        "reason": "run baseline training",
        "source": "script",
        "timeout_seconds": 300,
        "env_overrides": {},
        "writable_paths": ["/tmp/demo-repo"],
        "network_access": "none",
        "execution_profile_id": "test-local",
        "execution_profile_fingerprint": "profile-hash",
    }


def _build_approval_record(action: dict) -> dict:
    return {
        "approval_id": "approval_001",
        "action_id": action["action_id"],
        "action_hash": compute_action_hash(action),
        "decision": "approved",
        "reviewer": "human",
        "risk_level": "medium",
        "reviewed_at": "2026-07-17T00:00:00+00:00",
        "comment": None,
    }


def _supervisor_result(
    run_state,
    *,
    ok: bool,
    end_reason: str = "exited",
) -> dict:
    attempt = (
        Path(run_state["run_dir"])
        / "execution"
        / "attempts"
        / "exec-test"
    )
    attempt.mkdir(parents=True)
    stdout_path = attempt / "stdout.log"
    stderr_path = attempt / "stderr.log"
    combined_path = attempt / "combined.log"
    record_path = attempt / "process_record.json"
    stdout_path.write_text("training started\n", encoding="utf-8")
    stderr_path.write_text(
        "" if ok else "RuntimeError: CUDA out of memory\n",
        encoding="utf-8",
    )
    combined_path.write_text(
        "[stdout]\ntraining started\n"
        if ok
        else "[stderr]\nRuntimeError: CUDA out of memory\n",
        encoding="utf-8",
    )
    record_path.write_text("{}\n", encoding="utf-8")
    return {
        "ok": ok,
        "returncode": 0 if ok else 1,
        "end_reason": end_reason,
        "stdout": "training started" if ok else "",
        "stderr": "" if ok else "RuntimeError: CUDA out of memory",
        "combined_output": "training started" if ok else "CUDA OOM",
        "timeout": end_reason == "timeout",
        "cancelled": end_reason == "cancelled",
        "cancellation_reason": None,
        "log_truncated": False,
        "execution_id": "exec-test",
        "execution_profile_id": "test-local",
        "execution_backend": "local",
        "resource_usage": {"peak_rss_bytes": 1024},
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "combined_log_path": str(combined_path),
        "process_record_path": str(record_path),
    }


def test_executor_runs_command_when_approved(run_state) -> None:
    pending_action = _build_pending_action()
    state = {
        **run_state,
        "user_approval": "approved",
        "pending_action": pending_action,
        "approval_record": _build_approval_record(pending_action),
    }
    fake_result = _supervisor_result(run_state, ok=True)

    with patch(
        "app.nodes.executor_node.run_action_safe",
        return_value=fake_result,
    ) as mocked_run:
        result = executor_node(state)

    expected_action = ExecutableAction.model_validate(
        pending_action
    ).model_dump()
    mocked_run.assert_called_once_with(
        expected_action,
        state=state,
        stage="executor",
    )
    assert "final_status" not in result
    assert result["execution_result"]["ok"] is True
    assert result["execution_evidence"]
    assert result["execution_log_path"] == fake_result["combined_log_path"]
    assert result["active_execution_id"] == "exec-test"
    assert result["last_action_result"]["status"] == (
        "evidence_recorded"
    )
    assert result["last_action_result"]["end_reason"] == "exited"
    assert len(
        [
            item
            for item in result["artifact_records"]
            if item["producer_node"] == "executor"
        ]
    ) == 5
    assert "log_path" not in result


def test_executor_does_not_run_when_rejected(run_state) -> None:
    pending_action = _build_pending_action()
    state = {
        **run_state,
        "user_approval": "rejected",
        "pending_action": pending_action,
    }
    with patch("app.nodes.executor_node.run_action_safe") as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "rejected"


def test_executor_does_not_run_when_revise_requested(run_state) -> None:
    pending_action = _build_pending_action()
    state = {
        **run_state,
        "user_approval": "revise",
        "human_feedback": "请先缩小 batch size",
        "pending_action": pending_action,
    }
    with patch("app.nodes.executor_node.run_action_safe") as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "revise_requested"
    assert result["last_action_result"]["human_feedback"] == "请先缩小 batch size"


def test_executor_classifies_nonzero_exit_and_sets_log_path(
    run_state,
) -> None:
    pending_action = _build_pending_action()
    state = {
        **run_state,
        "user_approval": "approved",
        "pending_action": pending_action,
        "approval_record": _build_approval_record(pending_action),
    }
    fake_result = _supervisor_result(run_state, ok=False)

    with patch(
        "app.nodes.executor_node.run_action_safe",
        return_value=fake_result,
    ):
        result = executor_node(state)

    assert "final_status" not in result
    assert result["execution_result"]["returncode"] == 1
    assert result["execution_evidence"]["returncode"] == 1
    assert "active_stage_error" not in result


@pytest.mark.parametrize(
    ("reason", "category", "terminal", "final_status"),
    [
        ("exited", "paper_program", False, "failed"),
        ("timeout", "paper_program", False, "failed"),
        ("memory_limit", "paper_program", False, "failed"),
        ("cancelled", "user", True, "cancelled"),
        ("policy_denied", "user", True, "policy_blocked"),
        ("launch_error", "environment", True, "environment_blocked"),
        ("supervisor_error", "agent", True, "agent_failed"),
        ("orphan_cleanup", "agent", True, "agent_failed"),
    ],
)
def test_execution_end_reason_classification(
    reason,
    category,
    terminal,
    final_status,
) -> None:
    error, status = build_execution_stage_error(
        stage="executor",
        result={
            "end_reason": reason,
            "returncode": 1,
            "stderr": "failure",
            "resource_usage": {},
        },
        log_path=None,
    )

    assert error.category == category
    assert error.terminal is terminal
    assert status == final_status
