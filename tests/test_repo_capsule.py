from __future__ import annotations

"""Phase 26 §47: Git capsule 测试。"""

import subprocess
from pathlib import Path

import pytest

from app.config import settings
from app.workspace.errors import (
    WorkspaceNotPortableError,
)
from app.workspace.repo_capsule import (
    create_repository_capsule,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return result.stdout.strip()


def _clean_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    # ``git init -b main`` 需要 git >= 2.28；旧版本用 symbolic-ref 设置默认分支。
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(
        repo,
        "config",
        "user.email",
        "tests@example.com",
    )
    _git(repo, "config", "user.name", "Tests")
    (repo / ".gitignore").write_text(
        ".env\n", encoding="utf-8"
    )
    (repo / "train.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    _git(repo, "add", ".gitignore", "train.py")
    _git(repo, "commit", "-m", "initial")
    return repo


def test_capsule_preserves_commit_but_not_ignored_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(
        settings, "workspace_staging_root", staging
    )
    repo = _clean_repo(tmp_path)
    (repo / ".env").write_text(
        "TOKEN=secret\n", encoding="utf-8"
    )

    capsule = create_repository_capsule(
        repo_path=repo,
        destination=staging / "repo.bundle",
    )
    clone = tmp_path / "clone"
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            "main",
            str(capsule.bundle_path),
            str(clone),
        ],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    assert (
        _git(clone, "rev-parse", "HEAD")
        == capsule.identity.commit_sha
    )
    assert not (clone / ".env").exists()


def test_dirty_repo_is_not_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(
        settings, "workspace_staging_root", staging
    )
    repo = _clean_repo(tmp_path)
    (repo / "train.py").write_text(
        "VALUE = 2\n", encoding="utf-8"
    )

    with pytest.raises(
        WorkspaceNotPortableError,
        match="repository_dirty",
    ):
        create_repository_capsule(
            repo_path=repo,
            destination=staging / "repo.bundle",
        )
