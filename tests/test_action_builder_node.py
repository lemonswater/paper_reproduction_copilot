from __future__ import annotations

from unittest.mock import patch

from app.nodes.action_builder_node import action_builder_node
from app.schemas import ExecutionProfile
from app.tools.action_tools import compute_action_hash


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "demo-repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        writable_roots=[str(workspace)],
    )


def test_action_builder_builds_pending_action_from_first_run_command(
    tmp_path,
) -> None:
    profile = _profile(tmp_path)
    state = {
        "execution_profile_id": profile.profile_id,
        "repo_path": profile.workspace_root,
        "run_commands": [
            {
                "command": "python train.py --config configs/base.yaml",
                "cwd": profile.workspace_root,
                "reason": "run baseline training",
                "source": "script",
            },
            {
                "command": "python eval.py --ckpt outputs/best.pt",
                "cwd": profile.workspace_root,
                "reason": "run evaluation",
                "source": "script",
            },
        ],
    }

    with patch(
        "app.nodes.action_builder_node.get_execution_profile",
        return_value=profile,
    ):
        result = action_builder_node(state)
    action = result["pending_action"]

    assert action["action_type"] == "run_command"
    assert action["program"] == "python"
    assert action["args"] == [
        "train.py",
        "--config",
        "configs/base.yaml",
    ]
    assert action["cwd"] == profile.workspace_root
    assert action["reason"] == "run baseline training"
    assert action["source"] == "script"
    assert action["writable_paths"] == [profile.workspace_root]
    assert action["network_access"] == "none"
    assert action["resource_budget"] is None
    assert action["execution_profile_id"] == profile.profile_id
    assert action["action_id"]
    assert result["pending_action_hash"] == compute_action_hash(action)


def test_action_builder_returns_no_action_when_run_commands_is_empty() -> None:
    result = action_builder_node({"run_commands": []})

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
        "run_commands": [],
    }

    result = action_builder_node(state)

    assert result["pending_action"] == existing_action
    assert result["pending_action_hash"] == "known_hash"
