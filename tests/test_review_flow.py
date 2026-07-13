from unittest.mock import patch

import pytest

from app.nodes.human_review_node import human_review_node
from app.nodes.risk_check_node import risk_check_node
from app.tools.safe_shell_tools import assess_command_risk


@pytest.mark.parametrize(
    ("command", "risk_level", "blocked"),
    [
        ("rm -rf outputs", "blocked", True),
        ("python train.py", "medium", False),
        ("torchrun train.py", "medium", False),
    ],
)
def test_assess_command_risk_basic_cases(command: str, risk_level: str, blocked: bool) -> None:
    risk = assess_command_risk(command)

    assert risk.command == command
    assert risk.risk_level == risk_level
    assert risk.blocked is blocked
    assert risk.reason


def test_assess_command_risk_environment_change_requires_high_risk() -> None:
    risk = assess_command_risk("pip install torch")

    assert risk.risk_level == "high"
    assert risk.blocked is False
    assert "approval" in risk.reason


def test_risk_check_node_for_run_command_sets_risk_and_requires_approval() -> None:
    state = {"pending_action": {"type": "run_command", "command": "python train.py"}}

    result = risk_check_node(state)

    assert result["requires_approval"] is True
    assert result["error"] is None
    assert result["pending_action"]["risk"]["level"] == "medium"
    assert result["pending_action"]["risk"]["blocked"] is False


def test_risk_check_node_for_blocked_command_returns_error() -> None:
    state = {"pending_action": {"type": "run_command", "command": "rm -rf outputs"}}

    result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["error"]
    assert result["pending_action"]["risk"]["level"] == "blocked"
    assert result["pending_action"]["risk"]["blocked"] is True


@pytest.mark.parametrize("action_type", ["modify_config", "write_repo_file"])
def test_risk_check_node_repo_modification_requires_approval(action_type: str) -> None:
    state = {"pending_action": {"type": action_type, "path": "config.yaml"}}

    result = risk_check_node(state)

    assert result["requires_approval"] is True
    assert result["pending_action"]["risk"]["level"] == "high"
    assert result["pending_action"]["risk"]["blocked"] is False


def test_risk_check_node_without_pending_action_skips_review() -> None:
    result = risk_check_node({})

    assert result == {"requires_approval": False, "pending_action": None}


def test_human_review_node_skips_when_approval_not_required() -> None:
    result = human_review_node({"requires_approval": False})

    assert result == {"user_approval": "not_required"}


def test_human_review_node_reports_missing_action() -> None:
    result = human_review_node({"requires_approval": True})

    assert result == {"user_approval": "missing_action"}


def test_human_review_node_returns_structured_decision_and_feedback() -> None:
    state = {
        "requires_approval": True,
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "risk": {
                "level": "medium",
                "reason": "training or script execution requires approval",
                "blocked": False,
            },
        },
    }

    with patch(
        "app.nodes.human_review_node.interrupt",
        return_value={"decision": "approved", "feedback": "可以执行"},
    ):
        result = human_review_node(state)

    assert result == {"user_approval": "approved", "human_feedback": "可以执行"}


def test_human_review_node_accepts_string_decision() -> None:
    state = {
        "requires_approval": True,
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "risk": {
                "level": "medium",
                "reason": "training or script execution requires approval",
                "blocked": False,
            },
        },
    }

    with patch("app.nodes.human_review_node.interrupt", return_value="rejected"):
        result = human_review_node(state)

    assert result == {"user_approval": "rejected", "human_feedback": None}


def test_risk_check_and_human_review_work_together() -> None:
    state = {"pending_action": {"type": "run_command", "command": "python train.py"}}
    state.update(risk_check_node(state))

    with patch(
        "app.nodes.human_review_node.interrupt",
        return_value={"decision": "revise", "feedback": "先检查 batch size"},
    ):
        state.update(human_review_node(state))

    assert state["requires_approval"] is True
    assert state["pending_action"]["risk"]["level"] == "medium"
    assert state["user_approval"] == "revise"
    assert state["human_feedback"] == "先检查 batch size"
