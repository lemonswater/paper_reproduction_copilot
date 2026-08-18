from __future__ import annotations

from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.schemas import ExecutionProfile


def _action(workspace, **updates) -> dict:
    action = {
        "action_id": "action-1",
        "program": "python",
        "args": ["train.py"],
        "cwd": str(workspace),
        "source": "script",
        "reason": "test",
        "writable_paths": [str(workspace)],
        "network_access": "none",
        "execution_profile_id": "test",
        "execution_profile_fingerprint": "hash",
    }
    action.update(updates)
    return action


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        writable_roots=[str(workspace)],
        allowed_programs=["python"],
        network_policy="deny",
    )


def test_policy_rejects_network_when_profile_denies(
    tmp_path,
) -> None:
    profile = _profile(tmp_path)
    decision = evaluate_action_capabilities(
        raw_action=_action(
            profile.workspace_root,
            network_access="outbound",
        ),
        profile=profile,
    )

    assert decision.allowed is False
    assert any(
        item.code == "NETWORK_NOT_ALLOWED"
        for item in decision.violations
    )


def test_policy_rejects_writable_path_escape(tmp_path) -> None:
    profile = _profile(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    decision = evaluate_action_capabilities(
        raw_action=_action(
            profile.workspace_root,
            writable_paths=[str(outside)],
        ),
        profile=profile,
    )

    assert decision.allowed is False
    assert any(
        item.code == "WRITABLE_PATH_NOT_ALLOWED"
        for item in decision.violations
    )


def test_action_budget_cannot_expand_profile(tmp_path) -> None:
    profile = _profile(tmp_path)
    decision = evaluate_action_capabilities(
        raw_action=_action(
            profile.workspace_root,
            resource_budget={"max_processes": 1000},
        ),
        profile=profile,
    )

    assert decision.allowed is False
    assert any(
        item.code == "RESOURCE_BUDGET_EXPANSION"
        for item in decision.violations
    )