import sys

from app.execution.local_runner import LocalRunner
from app.schemas import ExecutionProfile


def test_local_runner_executes_inside_workspace(tmp_path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()

    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = LocalRunner(profile)

    result = runner.run_program(
        program=sys.executable,
        args=["-c", "from pathlib import Path; print(Path.cwd())"],
        cwd=str(workspace),
        timeout_seconds=10,
    )

    assert result["ok"] is True
    assert result["stdout"].strip() == str(workspace)


def test_local_runner_rejects_cwd_outside_workspace(tmp_path) -> None:
    workspace = tmp_path / "repo"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()

    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = LocalRunner(profile)

    result = runner.run_program(
        program=sys.executable,
        args=["-c", "print('should not run')"],
        cwd=str(outside),
        timeout_seconds=10,
    )

    assert result["ok"] is False
    assert "outside execution workspace" in result["stderr"]

import sys

from app.execution.local_runner import LocalRunner
from app.schemas import ExecutionProfile


def test_local_runner_executes_inside_workspace(tmp_path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()

    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = LocalRunner(profile)

    result = runner.run_program(
        program=sys.executable,
        args=["-c", "from pathlib import Path; print(Path.cwd())"],
        cwd=str(workspace),
        timeout_seconds=10,
    )

    assert result["ok"] is True
    assert result["stdout"].strip() == str(workspace)


def test_local_runner_rejects_cwd_outside_workspace(tmp_path) -> None:
    workspace = tmp_path / "repo"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()

    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = LocalRunner(profile)

    result = runner.run_program(
        program=sys.executable,
        args=["-c", "print('should not run')"],
        cwd=str(outside),
        timeout_seconds=10,
    )

    assert result["ok"] is False
    assert "outside execution workspace" in result["stderr"]