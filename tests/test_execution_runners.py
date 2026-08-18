from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.config import settings
from app.execution.local_runner import LocalRunner
from app.schemas import ExecutableAction, ExecutionProfile


def _profile(tmp_path) -> tuple[ExecutionProfile, str]:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    program = Path(sys.executable).name
    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        inherited_env_keys=[],
        env={"PATH": str(Path(sys.executable).resolve().parent)},
        allowed_programs=[program],
        writable_roots=[str(workspace)],
    )
    return profile, program


def _action(
    profile: ExecutionProfile,
    program: str,
    cwd: str,
) -> dict:
    return ExecutableAction(
        action_id="action-runner-test",
        program=program,
        args=["show_cwd.py"],
        cwd=cwd,
        source="script",
        reason="runner test",
        timeout_seconds=10,
        writable_paths=[profile.workspace_root],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint="test-hash",
    ).model_dump()


def test_local_runner_executes_inside_workspace(
    tmp_path,
    monkeypatch,
) -> None:
    profile, program = _profile(tmp_path)
    (Path(profile.workspace_root) / "show_cwd.py").write_text(
        "from pathlib import Path\nprint(Path.cwd())\n",
        encoding="utf-8",
    )
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "runs_dir", runs_dir)
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    result = LocalRunner(profile).run(
        _action(profile, program, profile.workspace_root),
        run_dir=str(run_dir),
        stage="runner_test",
    )

    assert result["ok"] is True
    assert result["end_reason"] == "exited"
    assert result["stdout"].strip() == profile.workspace_root
    assert Path(result["process_record_path"]).is_file()


def test_local_runner_rejects_cwd_outside_workspace(tmp_path) -> None:
    profile, program = _profile(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(ValueError, match="位于执行工作区之外"):
        LocalRunner(profile).run(
            _action(profile, program, str(outside)),
            run_dir=str(tmp_path / "runs" / "run-1"),
            stage="runner_test",
        )
