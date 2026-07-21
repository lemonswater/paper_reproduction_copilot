from unittest.mock import patch

from app.nodes.executor_node import executor_node
from app.config import settings

def test_executor_runs_when_not_required(monkeypatch, tmp_path):
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