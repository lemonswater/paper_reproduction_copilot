from __future__ import annotations

from app.tools.action_tools import compute_action_hash


def test_action_hash_binds_network_and_budget() -> None:
    action = {
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/data/tianshaoqi24/demo",
        "env_overrides": {},
        "timeout_seconds": 300,
        "writable_paths": ["/data/tianshaoqi24/demo"],
        "network_access": "none",
        "resource_budget": None,
        "execution_profile_id": "test",
        "execution_profile_fingerprint": "profile-hash",
        "repo_patch_hash": None,
    }

    original = compute_action_hash(action)
    with_network = compute_action_hash(
        {**action, "network_access": "outbound"}
    )
    with_budget = compute_action_hash(
        {
            **action,
            "resource_budget": {
                "max_wall_time_seconds": 30,
                "max_processes": 4,
                "max_log_bytes_per_stream": 4096,
                "max_preview_bytes": 1024,
                "sample_interval_seconds": 0.2,
                "terminate_grace_seconds": 1,
            },
        }
    )

    assert original != with_network
    assert original != with_budget
