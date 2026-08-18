from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.schemas import FileRepairProposal
from app.tools.patch_tools import (
    apply_exact_replacements,
    build_patch_bundle,
    resolve_patch_target,
    sha256_file,
    validate_patch_bundle,
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


def test_exact_replacement_requires_unique_old_text():
    with pytest.raises(ValueError, match="必须恰好出现一次"):
        apply_exact_replacements(
            "value = 1\nvalue = 1\n",
            [
                {
                    "old_text": "value = 1",
                    "new_text": "value = 2",
                    "reason": "test",
                }
            ],
        )


def test_patch_path_cannot_escape_repo(tmp_path):
    repo = _make_repo(tmp_path)
    with pytest.raises(ValueError):
        resolve_patch_target(repo, "../outside.py")


def test_patch_path_cannot_target_env(tmp_path):
    repo = _make_repo(tmp_path)
    env_path = repo / ".env"
    env_path.write_text("SECRET=value\n", encoding="utf-8")
    with pytest.raises(ValueError):
        resolve_patch_target(repo, ".env")


def test_build_patch_bundle_does_not_modify_source(tmp_path):
    repo = _make_repo(tmp_path)
    source = repo / "model.py"
    before_hash = sha256_file(source)

    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    assert Path(bundle.patch_path).exists()
    assert sha256_file(source) == before_hash
    assert "reshape" in Path(bundle.patch_path).read_text(encoding="utf-8")


def test_bundle_becomes_stale_when_patch_file_changes(tmp_path):
    repo = _make_repo(tmp_path)
    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    Path(bundle.patch_path).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="补丁文件在补丁包创建后发生了变化"):
        validate_patch_bundle(bundle)


def test_bundle_becomes_stale_when_source_changes(tmp_path):
    repo = _make_repo(tmp_path)
    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    (repo / "model.py").write_text("changed by user\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_patch_bundle(bundle)
