from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.tools.artifact_tools import sha256_file
from app.workspace.errors import (
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.schemas import RepositoryIdentity


@dataclass(frozen=True)
class RepositoryCapsule:
    identity: RepositoryIdentity
    bundle_path: Path
    sha256: str
    size_bytes: int


def _run_git(
    repo: Path,
    args: list[str],
    *,
    timeout: float | None = None,
) -> str:
    """只执行代码中固定构造的 token，不接受 shell command 字符串。"""

    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=(timeout or settings.workspace_git_timeout_seconds),
        shell=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            # 禁止 Git 调用交互式 credential helper。
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise WorkspaceIntegrityError(
            f"Git command failed：git {' '.join(args[:2])}；"
            f"{message[:500]}"
        )
    return completed.stdout.strip()


def _require_clean_repository(repo: Path) -> tuple[str, str]:
    if not repo.is_dir():
        raise WorkspaceIntegrityError(f"repo 不存在：{repo}")

    top = Path(
        _run_git(repo, ["rev-parse", "--show-toplevel"])
    ).resolve()
    if top != repo:
        raise WorkspaceIntegrityError(
            "repo_path 必须是 Git top-level，不能是任意子目录"
        )

    status = _run_git(
        repo,
        ["status", "--porcelain=v1", "--untracked-files=all"],
    )
    if status:
        raise WorkspaceNotPortableError(
            "repository_dirty：不会自动 stash/reset/commit"
        )

    try:
        branch = _run_git(
            repo,
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
        )
    except WorkspaceIntegrityError as exc:
        # symbolic-ref 在 detached HEAD 下返回非 0。这里应转成“不可迁移”，
        # 而不是误报为 bundle 内容损坏。
        raise WorkspaceNotPortableError(
            "detached_head：第一版要求有命名 branch"
        ) from exc

    commit = _run_git(repo, ["rev-parse", "HEAD"])
    return branch, commit


def _reject_unsupported_repository_features(repo: Path) -> None:
    gitmodules = repo / ".gitmodules"
    if gitmodules.exists():
        raise WorkspaceNotPortableError(
            "git_submodule_unsupported"
        )

    # 没安装 git-lfs 时命令可能失败；再检查 attributes 中的常见标记。
    attributes = repo / ".gitattributes"
    if attributes.is_file():
        text = attributes.read_text(
            encoding="utf-8",
            errors="replace",
        )
        if "filter=lfs" in text:
            raise WorkspaceNotPortableError("git_lfs_unsupported")


def inspect_repository_identity(
    repo_path: str | Path,
) -> RepositoryIdentity:
    """即使 dirty，也记录当前可验证的 commit/branch 与 feature 状态。"""

    repo = Path(repo_path).expanduser().resolve()
    top = Path(
        _run_git(repo, ["rev-parse", "--show-toplevel"])
    ).resolve()
    if top != repo:
        raise WorkspaceIntegrityError("repo_path 不是 Git top-level")

    commit = _run_git(repo, ["rev-parse", "HEAD"])
    branch_result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=settings.workspace_git_timeout_seconds,
        shell=False,
    )
    branch = branch_result.stdout.strip() or "<detached>"
    status = _run_git(
        repo,
        ["status", "--porcelain=v1", "--untracked-files=all"],
    )
    attributes = repo / ".gitattributes"
    has_lfs = (
        attributes.is_file()
        and "filter=lfs"
        in attributes.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )
    return RepositoryIdentity(
        commit_sha=commit,
        branch=branch,
        clean=not bool(status),
        bundle_logical_path=None,
        has_submodules=(repo / ".gitmodules").exists(),
        has_lfs=has_lfs,
    )


def create_repository_capsule(
    *,
    repo_path: str | Path,
    destination: Path,
) -> RepositoryCapsule:
    repo = Path(repo_path).expanduser().resolve()
    branch, commit = _require_clean_repository(repo)
    _reject_unsupported_repository_features(repo)

    destination = destination.resolve()
    staging_root = settings.workspace_staging_root.resolve()
    if staging_root not in destination.parents:
        raise WorkspaceIntegrityError(
            "repository bundle 必须写入 WORKSPACE_STAGING_ROOT"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise WorkspaceIntegrityError("bundle destination 已存在")

    # 必须传命名 ref。Git 官方文档指出仅传不可解析为 ref 的 commit
    # 可能得到 empty bundle。
    _run_git(
        repo,
        ["bundle", "create", str(destination), branch],
    )
    _run_git(repo, ["bundle", "verify", str(destination)])

    size = destination.stat().st_size
    if size > settings.workspace_max_file_bytes:
        destination.unlink(missing_ok=True)
        raise WorkspaceNotPortableError(
            "repository_bundle_too_large"
        )

    return RepositoryCapsule(
        identity=RepositoryIdentity(
            commit_sha=commit,
            branch=branch,
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
            has_submodules=False,
            has_lfs=False,
        ),
        bundle_path=destination,
        sha256=sha256_file(destination),
        size_bytes=size,
    )
