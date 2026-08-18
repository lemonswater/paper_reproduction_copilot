from __future__ import annotations

import pytest

from app.config import settings
from app.execution.environment import build_minimal_environment
from app.schemas import ExecutableAction, ExecutionProfile


class _NullSecretService:
    """测试用空 SecretService，不解析任何 Secret。"""

    def resolve(self, *, reference, use, actor):
        raise RuntimeError("不应被调用")


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        inherited_env_keys=["PATH", "LANG"],
        allowed_action_env_keys=["OMP_NUM_THREADS"],
        allowed_programs=["python"],
        writable_roots=[str(workspace)],
    )


def _action(profile: ExecutionProfile) -> ExecutableAction:
    return ExecutableAction(
        action_id="action-1",
        program="python",
        args=["train.py"],
        cwd=profile.workspace_root,
        source="script",
        reason="test",
        env_overrides={"OMP_NUM_THREADS": "2"},
        writable_paths=[profile.workspace_root],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint="hash",
    )


def test_minimal_env_does_not_inherit_agent_secret(
    tmp_path,
    monkeypatch,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile)
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(settings, "runs_dir", runs_dir)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")

    result = build_minimal_environment(
        profile=profile,
        action=action,
        run_dir=run_dir,
        execution_id="exec-1",
        secret_service=_NullSecretService(),
    )

    assert "OPENAI_API_KEY" not in result.env
    assert result.env["OMP_NUM_THREADS"] == "2"
    assert result.env["HOME"].startswith(str(run_dir))


def test_action_cannot_override_unapproved_env(
    tmp_path,
    monkeypatch,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile).model_copy(
        update={"env_overrides": {"UNAPPROVED": "1"}}
    )
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    with pytest.raises(ValueError, match="未被 profile 允许"):
        build_minimal_environment(
            profile=profile,
            action=action,
            run_dir=run_dir,
            execution_id="exec-1",
            secret_service=_NullSecretService(),
        )
