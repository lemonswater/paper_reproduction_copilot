from __future__ import annotations

from copy import deepcopy

import pytest

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
)
from app.schemas import ExecutionProfile, ResourceBudget
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


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        allowed_action_env_keys=["CUDA_VISIBLE_DEVICES"],
        allowed_programs=["python"],
        writable_roots=[str(workspace)],
        network_policy="deny",
        budget=ResourceBudget(max_wall_time_seconds=60),
    )


def test_profile_hash_changes_when_network_policy_changes(
    tmp_path,
) -> None:
    profile = _profile(tmp_path)
    original = compute_execution_profile_fingerprint(profile)
    changed = compute_execution_profile_fingerprint(
        profile.model_copy(update={"network_policy": "allow"})
    )

    assert original != changed


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [
        ("allowed_programs", ["python", "pytest"]),
        (
            "allowed_action_env_keys",
            ["CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS"],
        ),
        ("writable_roots", ["/tmp/other-workspace"]),
        (
            "budget",
            ResourceBudget(max_wall_time_seconds=120),
        ),
        ("conda_prefix", "/tmp/conda-prefix"),
        ("enforcement_mode", "strict"),
    ],
)
def test_profile_hash_covers_execution_security_fields(
    tmp_path,
    field,
    changed_value,
) -> None:
    profile = _profile(tmp_path)
    changed = profile.model_copy(update={field: changed_value})

    assert compute_execution_profile_fingerprint(
        profile
    ) != compute_execution_profile_fingerprint(changed)
