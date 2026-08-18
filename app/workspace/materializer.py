from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.storage.ports import BlobStore
from app.workspace.capabilities import explain_compatibility
from app.workspace.errors import (
    WorkerCapabilityError,
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.paths import (
    create_run_layout_at,
    require_workspace_relative_path,
    resolve_inside,
)
from app.workspace.repository import validate_manifest_hash
from app.workspace.schemas import (
    JobRequirements,
    WorkerIdentity,
    WorkspaceBinding,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_component(value: str, *, field: str) -> str:
    if not value or Path(value).name != value or value in {".", ".."}:
        raise WorkspaceIntegrityError(f"无效 {field}：{value!r}")
    return value


def _entry_target(
    *,
    staging_root: Path,
    entry: WorkspaceBlobEntry,
) -> Path:
    logical = require_workspace_relative_path(entry.logical_path)
    first = logical.parts[0]
    if first not in {"source", "capsule", "run"}:
        raise WorkspaceIntegrityError(
            f"未知 workspace entry scope：{first}"
        )

    expected_scope = {
        "paper": "source",
        "input_log": "source",
        "repository_bundle": "capsule",
        "run_artifact": "run",
        "process_record": "run",
        "process_log": "run",
    }[entry.role]
    if first != expected_scope:
        raise WorkspaceIntegrityError(
            f"entry role 与 logical_path 不匹配：{entry.role}"
        )
    return resolve_inside(staging_root, entry.logical_path)


def _copy_verified_blob(
    *,
    blob_store: BlobStore,
    entry: WorkspaceBlobEntry,
    target: Path,
) -> None:
    opened = blob_store.open(entry.object_key)
    if (
        opened.stat.sha256 != entry.sha256
        or opened.stat.size_bytes != entry.size_bytes
    ):
        opened.body.close()
        raise WorkspaceIntegrityError(
            "Blob metadata 与 Workspace Manifest 不一致"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    copied = 0
    try:
        with target.open("xb") as output:
            while True:
                chunk = opened.body.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                copied += len(chunk)
                if copied > entry.size_bytes:
                    raise WorkspaceIntegrityError(
                        "Blob stream 超过 manifest size"
                    )
            output.flush()
            os.fsync(output.fileno())
    finally:
        opened.body.close()

    if copied != entry.size_bytes or digest.hexdigest() != entry.sha256:
        raise WorkspaceIntegrityError(
            f"Blob 内容完整性失败：{entry.logical_path}"
        )

    # 只恢复普通可读文件和可执行位，不恢复 suid/sgid/sticky bits。
    target.chmod(0o755 if entry.executable else 0o644)


def _run_git(args: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=(str(cwd) if cwd is not None else None),
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        timeout=settings.workspace_git_timeout_seconds,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise WorkspaceIntegrityError(
            f"Git materialization failed：{message[:500]}"
        )
    return completed.stdout.strip()


def _validate_repository_symlinks(repo: Path) -> None:
    for path in repo.rglob("*"):
        if ".git" in path.relative_to(repo).parts:
            continue
        if not path.is_symlink():
            continue
        raw_target = os.readlink(path)
        if Path(raw_target).is_absolute():
            raise WorkspaceIntegrityError(
                f"仓库包含绝对 symlink：{path.relative_to(repo)}"
            )
        resolved = (path.parent / raw_target).resolve()
        if resolved != repo and repo not in resolved.parents:
            raise WorkspaceIntegrityError(
                f"仓库 symlink 逃逸 workspace：{path.relative_to(repo)}"
            )


def _clone_repository(
    *,
    staging_root: Path,
    manifest: WorkspaceManifest,
) -> Path:
    bundle = staging_root / "capsule" / "repository.bundle"
    if not bundle.is_file():
        raise WorkspaceIntegrityError("blob-entry manifest 缺少 Git bundle")

    # list-heads 不依赖当前 Git repository，可在 clone 前拒绝损坏的 bundle。
    _run_git(["bundle", "list-heads", str(bundle)])
    repo = staging_root / "repo"
    _run_git(
        [
            "clone",
            "--branch",
            manifest.repository.branch,
            "--single-branch",
            str(bundle),
            str(repo),
        ]
    )

    # clone 后再在目标 repository 上执行完整 prerequisite 校验。
    _run_git(["bundle", "verify", str(bundle)], cwd=repo)

    commit = _run_git(["rev-parse", "HEAD"], cwd=repo)
    if commit != manifest.repository.commit_sha:
        raise WorkspaceIntegrityError(
            "materialized repository commit 不匹配"
        )
    status = _run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo,
    )
    if status:
        raise WorkspaceIntegrityError(
            "materialized repository 不是 clean state"
        )
    _validate_repository_symlinks(repo)
    return repo


class WorkspaceMaterializer:
    def __init__(self, *, blob_store: BlobStore):
        self.blob_store = blob_store

    def _epoch_root(
        self,
        *,
        worker: WorkerIdentity,
        job_id: str,
        assignment_epoch: int,
    ) -> Path:
        _safe_component(job_id, field="job_id")
        configured = settings.worker_workspace_root.resolve()
        declared = Path(worker.workspace_root).resolve()
        if declared != configured:
            raise WorkspaceIntegrityError(
                "Worker identity workspace_root 与本进程配置不一致"
            )
        return (
            configured
            / "jobs"
            / job_id
            / "epochs"
            / f"{assignment_epoch:08d}"
        ).resolve()

    def planned_binding(
        self,
        *,
        worker: WorkerIdentity,
        manifest: WorkspaceManifest,
        requirements: JobRequirements,
        assignment_epoch: int,
        assignment_token: str,
    ) -> WorkspaceBinding:
        explanation = explain_compatibility(
            requirements=requirements,
            worker=worker,
            affinity_host_id=(
                None if manifest.portable else manifest.source_host_id
            ),
        )
        if not explanation.compatible:
            raise WorkerCapabilityError(
                "Worker 不满足 workspace requirement："
                + ",".join(explanation.reasons)
            )

        now = utc_now()
        mode = manifest.resolved_materialization_mode()

        if mode == "host_paths":
            if manifest.source_paths is None:
                raise WorkspaceNotPortableError(
                    "host_paths manifest 缺少 source_paths"
                )
            source = manifest.source_paths
            if source.run_dir is None:
                # 初始 host-affine Job 仍使用原始 RUNS_DIR；run_context 会创建它。
                run_dir = str(
                    (
                        settings.runs_dir.resolve()
                        / _safe_component(manifest.run_id, field="run_id")
                    ).resolve()
                )
            else:
                run_dir = str(Path(source.run_dir).resolve())
            return WorkspaceBinding(
                assignment_id=f"was_{uuid4().hex}",
                assignment_epoch=assignment_epoch,
                assignment_token=assignment_token,
                job_id=manifest.job_id,
                run_id=manifest.run_id,
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                manifest_generation=manifest.generation,
                worker_session_id=worker.worker_session_id,
                host_id=worker.host_id,
                workspace_root=str(Path(run_dir).parent),
                run_dir=run_dir,
                repo_path=source.repo_path,
                paper_path=source.paper_path,
                log_path=source.log_path,
                status="materializing",
                created_at=now,
                updated_at=now,
            )

        epoch_root = self._epoch_root(
            worker=worker,
            job_id=manifest.job_id,
            assignment_epoch=assignment_epoch,
        )
        return WorkspaceBinding(
            assignment_id=f"was_{uuid4().hex}",
            assignment_epoch=assignment_epoch,
            assignment_token=assignment_token,
            job_id=manifest.job_id,
            run_id=manifest.run_id,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            manifest_generation=manifest.generation,
            worker_session_id=worker.worker_session_id,
            host_id=worker.host_id,
            workspace_root=str(epoch_root),
            run_dir=str(epoch_root / "run"),
            repo_path=str(epoch_root / "repo"),
            paper_path=str(epoch_root / "source" / "paper.pdf"),
            log_path=(
                str(epoch_root / "source" / "external.log")
                if any(item.role == "input_log" for item in manifest.entries)
                else None
            ),
            status="materializing",
            created_at=now,
            updated_at=now,
        )

    def materialize(
        self,
        *,
        manifest: WorkspaceManifest,
        binding: WorkspaceBinding,
    ) -> WorkspaceBinding:
        validate_manifest_hash(manifest)
        mode = manifest.resolved_materialization_mode()

        if not manifest.portable and binding.host_id != manifest.source_host_id:
            raise WorkspaceNotPortableError("host affinity 不匹配")

        if mode == "host_paths":
            for path in (
                Path(binding.repo_path),
                Path(binding.paper_path),
            ):
                if not path.exists():
                    raise WorkspaceNotPortableError(
                        f"affinity host source 不存在：{path}"
                    )
            create_run_layout_at(Path(binding.run_dir))
            return binding.model_copy(
                update={"status": "ready", "updated_at": utc_now()}
            )

        # 下方原 portable Blob copy + git clone 分支保持不变，
        # 现在也会被 non-portable/blob_entries Manifest 使用。

        final_root = Path(binding.workspace_root).resolve()
        parent = final_root.parent
        parent.mkdir(parents=True, exist_ok=True)
        staging = parent / f".{final_root.name}.{uuid4().hex}.staging"

        if final_root.exists():
            marker = final_root / ".workspace-binding.json"
            if not marker.is_file():
                raise WorkspaceIntegrityError(
                    "epoch root 已存在但没有 binding marker"
                )
            existing = WorkspaceBinding.model_validate_json(
                marker.read_text(encoding="utf-8")
            )
            if (
                existing.assignment_token != binding.assignment_token
                or existing.manifest_hash != manifest.manifest_hash
            ):
                raise WorkspaceIntegrityError(
                    "epoch root 已被其他 assignment 使用"
                )
            return existing

        try:
            staging.mkdir(mode=0o700)
            for entry in manifest.entries:
                target = _entry_target(
                    staging_root=staging,
                    entry=entry,
                )
                _copy_verified_blob(
                    blob_store=self.blob_store,
                    entry=entry,
                    target=target,
                )

            repo = _clone_repository(
                staging_root=staging,
                manifest=manifest,
            )
            run_dir = staging / "run"
            create_run_layout_at(run_dir)

            # rename 前构造最终路径，marker 不能记录 staging path。
            now = utc_now()
            ready = binding.model_copy(
                update={
                    "repo_path": str(final_root / repo.relative_to(staging)),
                    "run_dir": str(final_root / "run"),
                    "paper_path": str(final_root / "source" / "paper.pdf"),
                    "log_path": (
                        str(final_root / "source" / "external.log")
                        if binding.log_path is not None
                        else None
                    ),
                    "status": "ready",
                    "updated_at": now,
                }
            )
            marker = staging / ".workspace-binding.json"
            marker.write_text(
                ready.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
            marker.chmod(stat.S_IRUSR | stat.S_IWUSR)
            os.replace(staging, final_root)
            return ready
        finally:
            if staging.exists():
                shutil.rmtree(staging)
