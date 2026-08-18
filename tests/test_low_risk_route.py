from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.graph import route_after_risk_check
from app.nodes.executor_node import executor_node
from app.nodes.risk_check_node import risk_check_node
from app.schemas import ExecutionProfile
from app.tools.safe_shell_tools import assess_action_risk


def test_assess_action_risk_returns_low_for_echo() -> None:
    risk = assess_action_risk(
        {
            "action_type": "run_command",
            "program": "echo",
            "args": ["hello"],
            "cwd": ".",
        }
    )

    assert risk.risk_level == "low"
    assert risk.blocked is False


def test_assess_action_risk_returns_medium_for_python_script() -> None:
    risk = assess_action_risk(
        {
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py"],
            "cwd": ".",
        }
    )

    assert risk.risk_level == "medium"
    assert risk.blocked is False


def test_assess_action_risk_returns_blocked_for_rm() -> None:
    risk = assess_action_risk(
        {
            "action_type": "run_command",
            "program": "rm",
            "args": ["-rf", "outputs"],
            "cwd": ".",
        }
    )

    assert risk.risk_level == "blocked"
    assert risk.blocked is True


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        allowed_programs=["echo"],
        writable_roots=[str(workspace)],
    )


def _action(profile: ExecutionProfile, program: str) -> dict:
    return {
        "action_id": f"action-{program}",
        "action_type": "run_command",
        "program": program,
        "args": ["hello"] if program == "echo" else ["-rf", "outputs"],
        "cwd": profile.workspace_root,
        "source": "script",
        "reason": "route test",
        "timeout_seconds": 30,
        "env_overrides": {},
        "writable_paths": [],
        "network_access": "none",
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": "profile-hash",
    }


def test_risk_check_node_skips_review_for_low_risk_action(
    tmp_path,
    run_state,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile, "echo")
    state = {
        **run_state,
        "pending_action": action,
        "pending_action_hash": "demo-hash",
    }

    with patch(
        "app.nodes.risk_check_node.get_execution_profile",
        return_value=profile,
    ):
        result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["user_approval"] == "not_required"
    assert result["pending_action"]["risk"]["level"] == "low"
    assert result.get("final_status") is None


def test_risk_check_node_marks_blocked_action(
    tmp_path,
    run_state,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile, "rm")
    state = {
        **run_state,
        "pending_action": action,
        "pending_action_hash": "demo-hash",
    }

    with patch(
        "app.nodes.risk_check_node.get_execution_profile",
        return_value=profile,
    ):
        result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["final_status"] == "policy_blocked"
    assert result["active_stage_error"]["terminal"] is True
    assert result["pending_action"]["risk"]["level"] == "blocked"


def test_route_after_risk_check_goes_to_preflight_when_not_required() -> None:
    state = {
        "requires_approval": False,
        "user_approval": "not_required",
    }

    assert route_after_risk_check(state) == "preflight_check"


def test_route_after_risk_check_goes_to_final_report_when_blocked() -> None:
    state = {
        "requires_approval": False,
        "final_status": "blocked",
    }

    assert route_after_risk_check(state) == "final_report"


def test_executor_runs_when_user_approval_is_not_required(
    tmp_path,
    run_state,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile, "echo")
    attempt = Path(run_state["run_dir"]) / "execution" / "attempts" / "echo"
    attempt.mkdir(parents=True)
    paths = {
        "stdout_path": attempt / "stdout.log",
        "stderr_path": attempt / "stderr.log",
        "combined_log_path": attempt / "combined.log",
        "process_record_path": attempt / "process_record.json",
    }
    for path in paths.values():
        path.write_text("hello\n", encoding="utf-8")
    fake_result = {
        "ok": True,
        "returncode": 0,
        "end_reason": "exited",
        "stdout": "hello\n",
        "stderr": "",
        "combined_output": "hello\n",
        "execution_id": "echo",
        "resource_usage": {},
        **{key: str(value) for key, value in paths.items()},
    }
    state = {
        **run_state,
        "pending_action": action,
        "user_approval": "not_required",
    }

    with patch(
        "app.nodes.executor_node.run_action_safe",
        return_value=fake_result,
    ):
        result = executor_node(state)

    assert "final_status" not in result
    assert result["execution_evidence"]
    assert result["execution_result"]["ok"] is True
    assert result["last_action_result"]["status"] == (
        "evidence_recorded"
    )
    assert result["execution_log_path"] == str(paths["combined_log_path"])
