from copy import deepcopy

from app.tools.action_tools import compute_action_hash


def _action() -> dict:
    return {
        "action_id": "action_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/tmp/repo",
        "source": "script",
        "reason": "test",
        "timeout_seconds": 300,
        "env_allowlist": {},
        "writable_paths": ["/tmp/repo"],
        "execution_profile_id": "paper-conda",
        "execution_profile_fingerprint": "fingerprint-a",
    }


def test_action_hash_changes_when_profile_changes() -> None:
    original = _action()
    changed = deepcopy(original)
    changed["execution_profile_fingerprint"] = "fingerprint-b"

    assert compute_action_hash(original) != compute_action_hash(changed)