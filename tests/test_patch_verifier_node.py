from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import settings
from app.execution.profile_store import compute_execution_profile_fingerprint
from app.schemas import ExecutionProfile, FileRepairProposal
from app.tools.patch_tools import (
    build_patch_bundle,
    verify_patch_in_worktree,
)


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _make_repo(tmp_path: Path) -> Path:
    """创建只供当前集成测试使用的最小 Git 仓库。"""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    source = repo / "model.py"
    source.write_text(
        "def forward(x):\n    return x.view(-1)\n",
        encoding="utf-8",
    )
    _git(repo, "add", "model.py")
    _git(repo, "commit", "-m", "initial")
    return repo


def _proposal() -> FileRepairProposal:
    return FileRepairProposal(
        proposal_id="file_repair_test",
        kind="patch",
        summary="replace view with reshape",
        root_cause="input may be non-contiguous",
        edits=[
            {
                "relative_path": "model.py",
                "reason": "avoid contiguous requirement",
                "replacements": [
                    {
                        "old_text": "return x.view(-1)",
                        "new_text": "return x.reshape(-1)",
                        "reason": "reshape supports non-contiguous input",
                    }
                ],
            }
        ],
        verification_targets=[],
        risks=["reshape may allocate a copy"],
        bounded=True,
    )


def test_patch_verification_uses_worktree_and_keeps_source_unchanged(
    tmp_path,
    monkeypatch,
):
    repo = _make_repo(tmp_path)
    source = repo / "model.py"
    original = source.read_text(encoding="utf-8")

    # CI 中用 local profile 验证调用链；CondaRunner 的
    # `conda run -p` 命令构造已在 Phase 10 的 Runner 测试覆盖。
    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(repo),
        artifact_root=str(tmp_path / "artifacts"),
    )
    monkeypatch.setattr(
        "app.tools.patch_tools.get_execution_profile",
        lambda profile_id: profile,
    )

    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    report = verify_patch_in_worktree(
        bundle=bundle,
        worktree_path=tmp_path / "worktrees" / bundle.patch_id,
        verification_targets=[],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=(
            compute_execution_profile_fingerprint(profile)
        ),
        run_dir=run_dir,
    )

    assert report.status == "structurally_valid"
    assert report.promotion_allowed is False
    assert report.structural_checks_passed is True
    assert report.behavioral_checks_run == 0
    assert report.verification_sha256
    assert report.execution_profile_id == profile.profile_id
    assert report.execution_backend == "local"
    assert profile.workspace_root == str(repo)
    assert source.read_text(encoding="utf-8") == original

    staged_source = Path(report.worktree_path) / "model.py"
    assert "reshape" in staged_source.read_text(encoding="utf-8")

from pathlib import Path

import pytest

from app.tools.patch_tools import validate_worktree_matches_patch


def _git_for_test(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


def test_reused_worktree_rejects_extra_tracked_change(
    patch_bundle,
    verified_worktree,
):
    # extra.py 必须存在于 fixture 初始 commit 中。
    (verified_worktree / "extra.py").write_text(
        "changed outside patch\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="diff scope mismatch"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_staged_change(
    patch_bundle,
    verified_worktree,
):
    extra = verified_worktree / "extra.py"
    extra.write_text("STAGED = True\n", encoding="utf-8")
    _git_for_test(verified_worktree, "add", "extra.py")

    with pytest.raises(ValueError, match="staged changes"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_missing_target(
    patch_bundle,
    verified_worktree,
):
    (verified_worktree / "train.py").unlink()

    with pytest.raises(ValueError, match="file missing"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_wrong_after_hash(
    patch_bundle,
    verified_worktree,
):
    (verified_worktree / "train.py").write_text(
        "VALUE = 999\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_changed_head(
    patch_bundle,
    verified_worktree,
):
    _git_for_test(verified_worktree, "add", "train.py")
    _git_for_test(verified_worktree, "commit", "-m", "changed head")

    with pytest.raises(ValueError, match="HEAD changed"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )