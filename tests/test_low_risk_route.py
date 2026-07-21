from app.tools.safe_shell_tools import assess_action_risk


def test_assess_action_risk_returns_low_for_echo() -> None:
    action = {
        "action_type": "run_command",
        "program": "echo",
        "args": ["hello"],
        "cwd": ".",
    }

    risk = assess_action_risk(action)

    assert risk.risk_level == "low"
    assert risk.blocked is False


def test_assess_action_risk_returns_medium_for_python_script() -> None:
    action = {
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": ".",
    }

    risk = assess_action_risk(action)

    assert risk.risk_level == "medium"
    assert risk.blocked is False


def test_assess_action_risk_returns_blocked_for_rm() -> None:
    action = {
        "action_type": "run_command",
        "program": "rm",
        "args": ["-rf", "outputs"],
        "cwd": ".",
    }

    risk = assess_action_risk(action)

    assert risk.risk_level == "blocked"
    assert risk.blocked is True


from app.nodes.risk_check_node import risk_check_node


def test_risk_check_node_skips_review_for_low_risk_action() -> None:
    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "echo",
            "args": ["hello"],
            "cwd": ".",
        },
        "pending_action_hash": "demo-hash",
    }

    result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["user_approval"] == "not_required"
    assert result["pending_action"]["risk"]["level"] == "low"
    assert result.get("final_status") is None

def test_risk_check_node_marks_blocked_action() -> None:
    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "rm",
            "args": ["-rf", "outputs"],
            "cwd": ".",
        },
        "pending_action_hash": "demo-hash",
    }

    result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["final_status"] == "blocked"
    assert result["error"]
    assert result["pending_action"]["risk"]["level"] == "blocked"


from app.graph import route_after_risk_check


def test_route_after_risk_check_goes_to_executor_when_not_required() -> None:
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

from unittest.mock import patch

from app.config import settings
from app.nodes.executor_node import executor_node


def test_executor_runs_when_user_approval_is_not_required(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "echo",
            "args": ["hello"],
            "cwd": ".",
        },
        "user_approval": "not_required",
        "output_files": [],
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "stdout": "hello\n",
        "stderr": "",
        "combined_output": "hello\n",
    }

    with patch("app.nodes.executor_node.run_action_safe", return_value=fake_result):
        result = executor_node(state)

    assert result["final_status"] == "succeeded"
    assert result["execution_result"]["ok"] is True
    assert result["execution_log_path"]