from app.nodes.action_builder_node import action_builder_node
from app.tools.action_tools import compute_action_hash


def test_action_builder_builds_pending_action_from_first_run_command() -> None:
    state = {
        "repo_path": "/tmp/demo-repo",
        "run_commands": [
            {
                "command": "python train.py --config configs/base.yaml",
                "cwd": "/tmp/demo-repo",
                "reason": "run baseline training",
                "source": "script",
            },
            {
                "command": "python eval.py --ckpt outputs/best.pt",
                "cwd": "/tmp/demo-repo",
                "reason": "run evaluation",
                "source": "script",
            },
        ],
    }

    result = action_builder_node(state)
    action = result["pending_action"]

    # 当前阶段只取第一条命令。
    assert action["action_type"] == "run_command"
    assert action["program"] == "python"
    assert action["args"] == ["train.py", "--config", "configs/base.yaml"]
    assert action["cwd"] == "/tmp/demo-repo"
    assert action["reason"] == "run baseline training"
    assert action["source"] == "script"
    assert action["writable_paths"] == ["/tmp/demo-repo"]
    assert action["action_id"]

    assert result["pending_action_hash"] == compute_action_hash(action)


def test_action_builder_returns_no_action_when_run_commands_is_empty() -> None:
    state = {"run_commands": []}

    result = action_builder_node(state)

    assert result["pending_action"] is None
    assert result["pending_action_hash"] is None
    assert result["final_status"] == "no_action"


def test_action_builder_keeps_existing_pending_action() -> None:
    existing_action = {
        "action_id": "action_manual_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["custom.py"],
        "cwd": "/tmp/custom",
        "reason": "manual injected action",
        "source": "script",
        "timeout_seconds": 300,
        "writable_paths": ["/tmp/custom"],
    }

    state = {
        "pending_action": existing_action,
        "pending_action_hash": "known_hash",
        "run_commands": [
            {
                "command": "python train.py",
                "cwd": "/tmp/demo-repo",
                "reason": "from plan",
                "source": "script",
            }
        ],
    }

    result = action_builder_node(state)

    assert result["pending_action"] == existing_action
    assert result["pending_action_hash"] == "known_hash"