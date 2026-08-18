from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.tools.patch_tools import (
    remove_patch_worktree,
    validate_patch_worktree_path,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


def test_cleanup_rejects_path_outside_current_run(tmp_path):
    run_dir = tmp_path / "run"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".git").write_text("gitdir: fixture\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside current run"):
        validate_patch_worktree_path(
            worktree_path=outside,
            run_dir=run_dir,
        )


def test_cleanup_removes_only_valid_run_worktree(
    patch_bundle,
    tmp_path,
):
    repo = Path(patch_bundle.repo_path)
    run_dir = tmp_path / "run"
    worktree = (
        run_dir
        / "execution"
        / "patch_worktrees"
        / patch_bundle.patch_id
    )
    worktree.parent.mkdir(parents=True)
    _git(
        repo,
        "worktree",
        "add",
        "--detach",
        str(worktree),
        patch_bundle.base_git_commit,
    )

    remove_patch_worktree(
        repo_path=str(repo),
        worktree_path=str(worktree),
        run_dir=str(run_dir),
    )

    assert not worktree.exists()