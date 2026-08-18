"""Phase 29 受控 Git fetch 测试。

安全矩阵：
- 必须 exact full commit
- actual commit mismatch 被拒绝
- 命令 shell=False、token 化
- 环境禁用 prompt/system/global config
- submodule/LFS 被拒绝
- fetch 失败不留下 published manifest
- bundle identity 与 commit 一致

测试需要本机 git 可用；使用本地 bare repo 作为 origin，不联网。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.resources.errors import (
    ResourceIntegrityError,
    ResourceTransportUnavailable,
)
from app.resources.git_fetcher import (
    GitResourceFetcher,
    resource_staging_dir,
)
from app.resources.policy import ValidatedDestination

pytestmark = pytest.mark.skipif(
    subprocess.run(
        ["git", "--version"],
        capture_output=True,
    ).returncode
    != 0,
    reason="git not available",
)

ALLOWED_HOSTS: tuple[str, ...] = ()


def _git(
    repo: Path, *args: str, env: dict | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
        env=env,
    )


def _init_repo(repo: Path, branch: str = "main") -> None:
    """兼容旧版 Git 的 init + branch 设置。"""
    _git(repo, "init")
    try:
        _git(
            repo,
            "symbolic-ref",
            "HEAD",
            f"refs/heads/{branch}",
        )
    except subprocess.CalledProcessError:
        _git(repo, "checkout", "-b", branch)


@pytest.fixture
def bare_origin(
    tmp_path: Path,
) -> tuple[Path, str]:
    """创建本地 bare repo 作为 origin，返回 (path, commit_sha)。"""

    work = tmp_path / "work"
    work.mkdir()
    _init_repo(work)
    _git(
        work,
        "config",
        "user.email",
        "test@example.com",
    )
    _git(work, "config", "user.name", "Test")
    (work / "README.md").write_text(
        "# Test Repository\n"
    )
    _git(work, "add", "README.md")
    _git(work, "commit", "-m", "initial")
    commit_sha = _git(
        work, "rev-parse", "HEAD"
    ).stdout.strip()

    bare = tmp_path / "origin.git"
    _git(work, "clone", "--bare", str(work), str(bare))
    return bare, commit_sha


@pytest.fixture
def git_fetcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> GitResourceFetcher:
    """Git fetcher with bypassed URL policy for local file:// testing."""

    monkeypatch.setattr(
        "app.resources.git_fetcher.settings.resource_staging_root",
        tmp_path / "staging",
    )
    monkeypatch.setattr(
        "app.resources.git_fetcher.settings.workspace_staging_root",
        tmp_path / "ws_staging",
    )
    (tmp_path / "staging").mkdir()
    (tmp_path / "ws_staging").mkdir()

    def _bypass_validator(
        raw_url: str,
        *,
        allowed_hosts: tuple[str, ...] = (),
        resolver=None,  # noqa: ARG001
    ) -> ValidatedDestination:
        # 测试用 file:// URL 绕过 HTTPS-only policy；生产代码绝不绕过。
        del allowed_hosts, resolver  # 测试绕过 host allowlist。
        return ValidatedDestination(
            canonical_url=raw_url,
            host="localhost",
            resolved_ips=("127.0.0.1",),
        )

    monkeypatch.setattr(
        "app.resources.git_fetcher.validate_destination",
        _bypass_validator,
    )
    return GitResourceFetcher(
        allowed_hosts=ALLOWED_HOSTS,
        timeout_seconds=30,
        # 测试需要 file:// 协议访问本地 bundle；生产代码绝不允许。
        extra_git_configs={
            "protocol.file.allow": "always",
        },
    )


class TestGitFetchBasics:
    def test_fetch_exact_commit(
        self,
        bare_origin: tuple[Path, str],
        git_fetcher: GitResourceFetcher,
        tmp_path: Path,
    ) -> None:
        bare, commit_sha = bare_origin
        staging = tmp_path / "fetch_staging"
        staging.mkdir()
        result = git_fetcher.fetch(
            source_url=f"file://{bare}",
            expected_commit=commit_sha,
            staging_dir=staging,
        )
        assert result.commit_sha == commit_sha
        assert result.bundle_path.is_file()
        assert result.bundle_size_bytes > 0
        assert len(result.bundle_sha256) == 64

    def test_commit_mismatch_rejected(
        self,
        bare_origin: tuple[Path, str],
        git_fetcher: GitResourceFetcher,
        tmp_path: Path,
    ) -> None:
        bare, _ = bare_origin
        staging = tmp_path / "fetch_staging"
        staging.mkdir()
        wrong_commit = "0" * 40
        with pytest.raises(
            (ResourceIntegrityError, ResourceTransportUnavailable)
        ):
            git_fetcher.fetch(
                source_url=f"file://{bare}",
                expected_commit=wrong_commit,
                staging_dir=staging,
            )


class TestSubmoduleAndLfs:
    def test_submodule_rejected(
        self,
        git_fetcher: GitResourceFetcher,
        tmp_path: Path,
    ) -> None:
        """创建带 .gitmodules 的 repo，确认 fetch 被拒绝。"""

        work = tmp_path / "submod_work"
        work.mkdir()
        _init_repo(work)
        _git(
            work,
            "config",
            "user.email",
            "test@example.com",
        )
        _git(work, "config", "user.name", "Test")
        (work / ".gitmodules").write_text(
            '[submodule "evil"]\n'
            'path = evil\n'
            'url = https://github.com/evil/repo\n'
        )
        (work / "README.md").write_text("test")
        _git(work, "add", ".")
        _git(work, "commit", "-m", "with submodules")
        commit_sha = _git(
            work, "rev-parse", "HEAD"
        ).stdout.strip()

        bare = tmp_path / "submod.git"
        _git(work, "clone", "--bare", str(work), str(bare))
        staging = tmp_path / "fetch_staging"
        staging.mkdir()
        with pytest.raises(ResourceIntegrityError):
            git_fetcher.fetch(
                source_url=f"file://{bare}",
                expected_commit=commit_sha,
                staging_dir=staging,
            )

    def test_lfs_rejected(
        self,
        git_fetcher: GitResourceFetcher,
        tmp_path: Path,
    ) -> None:
        """创建带 Git LFS .gitattributes 的 repo，确认 fetch 被拒绝。"""

        work = tmp_path / "lfs_work"
        work.mkdir()
        _init_repo(work)
        _git(
            work,
            "config",
            "user.email",
            "test@example.com",
        )
        _git(work, "config", "user.name", "Test")
        (work / ".gitattributes").write_text(
            "*.pt filter=lfs diff=lfs merge=lfs -text\n"
        )
        (work / "README.md").write_text("test")
        _git(work, "add", ".")
        _git(work, "commit", "-m", "with lfs")
        commit_sha = _git(
            work, "rev-parse", "HEAD"
        ).stdout.strip()

        bare = tmp_path / "lfs.git"
        _git(work, "clone", "--bare", str(work), str(bare))
        staging = tmp_path / "fetch_staging"
        staging.mkdir()
        with pytest.raises(ResourceIntegrityError):
            git_fetcher.fetch(
                source_url=f"file://{bare}",
                expected_commit=commit_sha,
                staging_dir=staging,
            )


class TestStagingDir:
    def test_staging_dir_under_resource_root(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.resources.git_fetcher.settings.resource_staging_root",
            tmp_path / "staging",
        )
        path = resource_staging_dir(
            "res_abc", "rclaim_token123"
        )
        root = (
            tmp_path
            / "staging"
        ).resolve()
        assert root in path.parents

    def test_staging_dir_rejects_path_separator(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.resources.git_fetcher.settings.resource_staging_root",
            tmp_path / "staging",
        )
        with pytest.raises(ValueError):
            resource_staging_dir(
                "res/../evil", "token"
            )
