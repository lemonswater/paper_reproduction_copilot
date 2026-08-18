from __future__ import annotations

"""Phase 29 受控 Git fetch。

Git 不能直接使用 HTTP downloader（需要协议交互），但仍使用同一 URL/DNS policy、
专用 Acquisition Worker 和网络层 egress guard。

安全约束：
- ``shell=False``，命令全部 token 化。
- 环境禁用 system/global config、交互 prompt、credential helper。
- ``protocol.file.allow=never``、``protocol.ext.allow=never``、
  ``submodule.recurse=false``。
- 必须锁定 exact commit，fetch 后再次比较；禁止 submodule、Git LFS。
- bundle 写入 ``WORKSPACE_STAGING_ROOT``（``create_repository_capsule`` 要求）。
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.resources.errors import (
    ResourceIntegrityError,
    ResourceTransportUnavailable,
)
from app.resources.policy import validate_destination
from app.workspace.repo_capsule import (
    create_repository_capsule,
)


@dataclass(frozen=True)
class GitFetchResult:
    repository_path: Path
    bundle_path: Path
    commit_sha: str
    bundle_sha256: str
    bundle_size_bytes: int


class GitResourceFetcher:
    def __init__(
        self,
        *,
        allowed_hosts: tuple[str, ...],
        timeout_seconds: float,
        extra_git_configs: dict[str, str] | None = None,
    ):
        self.allowed_hosts = allowed_hosts
        self.timeout_seconds = timeout_seconds
        self._extra_git_configs = extra_git_configs or {}

    def _env(
        self, isolated_home: Path
    ) -> dict[str, str]:
        isolated_home.mkdir(parents=True, exist_ok=True)
        return {
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "HOME": str(isolated_home),
            "XDG_CONFIG_HOME": str(
                isolated_home / ".config"
            ),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "GIT_PROTOCOL_FROM_USER": "0",
        }

    def _git_config_args(self) -> list[str]:
        """构建 git -c 参数。默认禁止 file/ext 协议和 submodule。

        ``extra_git_configs`` 可覆盖默认值（仅用于测试）。
        """
        configs = {
            "protocol.file.allow": "never",
            "protocol.ext.allow": "never",
            "submodule.recurse": "false",
        }
        configs.update(self._extra_git_configs)
        args: list[str] = []
        for key, value in configs.items():
            args.extend(["-c", f"{key}={value}"])
        return args

    def _run(
        self,
        cwd: Path,
        env: dict[str, str],
        *args: str,
    ) -> str:
        completed = subprocess.run(
            [
                "git",
                *self._git_config_args(),
                *args,
            ],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            shell=False,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            detail = (
                completed.stderr or completed.stdout
            ).strip()[:1000]
            raise ResourceTransportUnavailable(
                f"controlled git failed: {detail}"
            )
        return completed.stdout.strip()

    def fetch(
        self,
        *,
        source_url: str,
        expected_commit: str,
        staging_dir: Path,
    ) -> GitFetchResult:
        validated = validate_destination(
            source_url,
            allowed_hosts=self.allowed_hosts,
        )
        repo = staging_dir / "repo"
        home = staging_dir / "home"
        repo.mkdir(parents=True, exist_ok=False)
        env = self._env(home)

        self._run(repo, env, "init")
        # 兼容旧版 Git（无 --initial-branch）：init 后设置 HEAD。
        try:
            self._run(
                repo,
                env,
                "symbolic-ref",
                "HEAD",
                "refs/heads/acquired",
            )
        except ResourceTransportUnavailable:
            # 极旧 Git 无 symbolic-ref 时回退。
            pass
        self._run(
            repo,
            env,
            "remote",
            "add",
            "origin",
            validated.canonical_url,
        )
        self._run(
            repo,
            env,
            "fetch",
            "--depth=1",
            "--no-tags",
            "--no-recurse-submodules",
            "origin",
            expected_commit,
        )
        self._run(
            repo, env, "checkout", "--detach", "FETCH_HEAD"
        )
        actual_commit = self._run(
            repo, env, "rev-parse", "HEAD"
        ).lower()
        if actual_commit != expected_commit:
            raise ResourceIntegrityError(
                "Git fetch 得到的 commit 与 expected 不一致"
            )
        if (repo / ".gitmodules").exists():
            raise ResourceIntegrityError(
                "第一版拒绝 Git submodule"
            )
        attributes = repo / ".gitattributes"
        if attributes.is_file() and "filter=lfs" in (
            attributes.read_text(
                encoding="utf-8", errors="replace"
            )
        ):
            raise ResourceIntegrityError("第一版拒绝 Git LFS")

        # create_repository_capsule 要求命名 branch + bundle 写入
        # WORKSPACE_STAGING_ROOT。repo clone 可在 resource staging 下，
        # 但 bundle 必须在 workspace_staging_root 下。
        self._run(
            repo,
            env,
            "switch",
            "-c",
            f"acquired-{actual_commit[:12]}",
        )
        import uuid

        bundle_dir = (
            settings.workspace_staging_root.resolve()
            / f"resource_git_bundle_{uuid.uuid4().hex[:12]}"
        )
        bundle_dir.mkdir(parents=True, exist_ok=False)
        bundle_dest = bundle_dir / "repository.bundle"
        capsule = create_repository_capsule(
            repo_path=repo, destination=bundle_dest
        )
        return GitFetchResult(
            repository_path=repo,
            bundle_path=capsule.bundle_path,
            commit_sha=actual_commit,
            bundle_sha256=capsule.sha256,
            bundle_size_bytes=capsule.size_bytes,
        )

    def validate_fetched_repository(
        self,
        *,
        repo: Path,
        expected_commit: str,
    ) -> str:
        """对已存在的本地 repo 做 post-fetch integrity 校验（无需联网）。

        用于离线测试与 reconcile：检查 commit、submodule、LFS。
        """

        if not repo.is_dir():
            raise ResourceIntegrityError(
                f"repo 不存在：{repo}"
            )
        env = self._env(repo.parent / "home")
        actual_commit = self._run(
            repo, env, "rev-parse", "HEAD"
        ).lower()
        if actual_commit != expected_commit:
            raise ResourceIntegrityError(
                "Git repo commit 与 expected 不一致"
            )
        if (repo / ".gitmodules").exists():
            raise ResourceIntegrityError(
                "第一版拒绝 Git submodule"
            )
        attributes = repo / ".gitattributes"
        if attributes.is_file() and "filter=lfs" in (
            attributes.read_text(
                encoding="utf-8", errors="replace"
            )
        ):
            raise ResourceIntegrityError("第一版拒绝 Git LFS")
        return actual_commit


def resource_staging_dir(
    resource_id: str, claim_token: str
) -> Path:
    """每个 attempt 的隔离 staging 目录：``RESOURCE_STAGING_ROOT/<rid>/<claim_hash>``。

    清理前先确认路径位于 resource_staging_root 下，不能 glob 删除整个 resources/。
    """

    from app.observability.context import short_secret_hash

    root = settings.resource_staging_root.resolve()
    safe_id = Path(resource_id).name
    if safe_id != resource_id:
        raise ValueError("resource_id 含路径分隔符")
    claim_hash = short_secret_hash(claim_token)
    return (root / safe_id / claim_hash).resolve()
