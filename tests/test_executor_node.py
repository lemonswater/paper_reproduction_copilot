from unittest.mock import patch

from app.config import settings
from app.nodes.executor_node import executor_node
from app.tools.action_tools import compute_action_hash


def _build_pending_action() -> dict:
    # 构造当前 executor 期望消费的“结构化动作”。
    return {
        "action_id": "action_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/tmp/demo-repo",
        "reason": "run baseline training",
        "source": "script",
        "timeout_seconds": 300,
        "writable_paths": ["/tmp/demo-repo"],
    }


def _build_approval_record(action: dict) -> dict:
    # 当前 executor 在 user_approval == "approved" 时，
    # 还要求 approval_record 存在，且 action_hash 必须匹配。
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


def test_executor_runs_command_when_approved(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    pending_action = _build_pending_action()
    state = {
        "user_approval": "approved",
        "pending_action": pending_action,
        "approval_record": _build_approval_record(pending_action),
        "output_files": [],
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "stdout": "training started",
        "stderr": "",
        "combined_output": "training started",
        "timeout": False,
    }

    with patch("app.nodes.executor_node.run_action_safe", return_value=fake_result) as mocked_run:
        result = executor_node(state)

    mocked_run.assert_called_once_with(pending_action)
    assert result["final_status"] == "succeeded"
    assert result["execution_result"]["ok"] is True
    assert result["execution_log_path"]
    assert str(tmp_path / "execution.log") in result["output_files"]

    # 成功执行时不强制要求写回 log_path。
    assert "log_path" not in result


def test_executor_does_not_run_when_rejected() -> None:
    pending_action = _build_pending_action()
    state = {
        "user_approval": "rejected",
        "pending_action": pending_action,
    }

    with patch("app.nodes.executor_node.run_action_safe") as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "rejected"
    assert result["last_action_result"]["status"] == "rejected"


def test_executor_does_not_run_when_revise_requested() -> None:
    pending_action = _build_pending_action()
    state = {
        "user_approval": "revise",
        "human_feedback": "请先缩小 batch size",
        "pending_action": pending_action,
    }

    with patch("app.nodes.executor_node.run_action_safe") as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "revise_requested"
    assert result["last_action_result"]["human_feedback"] == "请先缩小 batch size"


def test_executor_marks_failed_and_sets_log_path_when_command_execution_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    pending_action = _build_pending_action()
    state = {
        "user_approval": "approved",
        "pending_action": pending_action,
        "approval_record": _build_approval_record(pending_action),
        "output_files": [],
    }

    fake_result = {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "RuntimeError: CUDA out of memory",
        "combined_output": "RuntimeError: CUDA out of memory",
        "timeout": False,
    }

    with patch("app.nodes.executor_node.run_action_safe", return_value=fake_result):
        result = executor_node(state)

    assert result["final_status"] == "failed"
    assert result["execution_result"]["ok"] is False
    assert result["execution_log_path"]
    assert result["log_path"] == result["execution_log_path"]