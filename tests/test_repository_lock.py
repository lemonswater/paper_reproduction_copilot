from __future__ import annotations

import pytest

from app.config import settings
from app.tools.repository_lock_tools import (
    RepositoryLockBusyError,
    acquire_repository_lock,
)


@pytest.fixture(autouse=True)
def _isolated_coordination_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings,
        "patch_coordination_dir",
        tmp_path / "coordination",
    )


def test_second_run_cannot_lock_same_repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    with acquire_repository_lock(
        repo,
        owner_run_id="run-a",
        timeout_seconds=0,
    ), pytest.raises(RepositoryLockBusyError), acquire_repository_lock(
        repo,
        owner_run_id="run-b",
        timeout_seconds=0,
    ):
        raise AssertionError("second lock must not be acquired")


def test_different_repositories_have_independent_locks(tmp_path):
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    repo_a.mkdir()
    repo_b.mkdir()

    with acquire_repository_lock(
        repo_a,
        owner_run_id="run-a",
        timeout_seconds=0,
    ), acquire_repository_lock(
        repo_b,
        owner_run_id="run-b",
        timeout_seconds=0,
    ):
        pass