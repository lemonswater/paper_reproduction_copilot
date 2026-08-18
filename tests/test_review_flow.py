from __future__ import annotations

from unittest.mock import patch

from app.nodes.executor_node import executor_node


def test_executor_runs_when_not_required(run_state):
    state = {
        **run_state,
        "pending_action": {
            "action_id": "action-review-flow",
            "action_type": "run_command",
            "program": "echo",
            "args": ["hello"],
            "cwd": ".",
            "source": "script",
            "reason": "test low risk command",
            "execution_profile_id": "test-local",
            "execution_profile_fingerprint": "profile-test",
        },
        "user_approval": "not_required",
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "end_reason": "exited",
        "stdout": "hello\n",
        "stderr": "",
        "combined_output": "hello\n",
        "execution_id": "exec-review-flow",
        "execution_profile_id": "test-local",
        "execution_backend": "local",
        "resource_usage": {},
    }

    with patch("app.nodes.executor_node.run_action_safe", return_value=fake_result):
        result = executor_node(state)

    assert "final_status" not in result
    assert result["execution_evidence"]
    assert result["execution_result"]["ok"] is True
    assert result["last_action_result"]["status"] == (
        "evidence_recorded"
    )
