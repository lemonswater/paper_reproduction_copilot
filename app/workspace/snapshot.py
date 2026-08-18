from __future__ import annotations

import mimetypes
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import settings
from app.schemas import ArtifactRecord
from app.storage.ports import BlobStore
from app.tools.artifact_tools import sha256_file
from app.workspace.errors import (
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.paths import (
    require_managed_run_root,
    require_workspace_relative_path,
)
from app.workspace.repo_capsule import (
    create_repository_capsule,
    inspect_repository_identity,
)
from app.workspace.repository import workspace_manifest_hash
from app.workspace.schemas import (
    ExternalDataReference,
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
    WorkspaceSourcePaths,
)

PROCESS_FILE_PATTERNS = (
    "execution/attempts/*/process_record.json",
    "execution/attempts/*/stdout.log",
    "execution/attempts/*/stderr.log",
    "execution/attempts/*/combined.log",
    "execution/control/*.runtime.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_object_key(sha256: str) -> str:
    return f"workspace/sha256/{sha256[:2]}/{sha256}"


def _media_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


class WorkspaceSnapshotter:
    def __init__(self, *, blob_store: BlobStore):
        self.blob_store = blob_store
        self.blob_store.ensure_ready()

    def _publish_entry(
        self,
        *,
        source: Path,
        logical_path: str,
        role: str,
        executable: bool = False,
    ) -> WorkspaceBlobEntry:
        require_workspace_relative_path(logical_path)
        resolved = source.resolve()
        if not resolved.is_file():
            raise WorkspaceIntegrityError(
                f"workspace source 不存在：{resolved}"
            )
        size = resolved.stat().st_size
        if size > settings.workspace_max_file_bytes:
            raise WorkspaceNotPortableError(
                f"workspace_file_too_large:{logical_path}"
            )

        digest = sha256_file(resolved)
        stat = self.blob_store.put_file(
            object_key=workspace_object_key(digest),
            source_path=resolved,
            expected_sha256=digest,
            expected_size=size,
            media_type=_media_type(resolved),
        )
        if stat.sha256 != digest or stat.size_bytes != size:
            raise WorkspaceIntegrityError(
                "BlobStore 返回的 workspace stat 不匹配"
            )
        return WorkspaceBlobEntry(
            logical_path=logical_path,
            role=role,
            object_key=stat.object_key,
            sha256=digest,
            size_bytes=size,
            media_type=_media_type(resolved),
            executable=executable,
        )

    def _build_manifest(
        self,
        *,
        job_id: str,
        run_id: str,
        generation: int,
        parent_manifest_id: str | None,
        source_host_id: str,
        source_worker_session_id: str | None,
        entries: list[WorkspaceBlobEntry],
        repository: RepositoryIdentity,
        external_data: list[ExternalDataReference],
        blocked_reasons: list[str],
        source_paths: WorkspaceSourcePaths | None,
        materialization_mode: str = "auto",
    ) -> WorkspaceManifest:
        total = sum(item.size_bytes for item in entries)
        if total > settings.workspace_max_total_bytes:
            blocked_reasons.append("workspace_total_size_exceeded")

        # 只有共享 Blob、clean repo 和全部外部引用可调度时才 portable。
        if self.blob_store.sharing_scope != "shared":
            blocked_reasons.append("blob_store_is_host_local")

        reasons = sorted(set(blocked_reasons))
        draft = WorkspaceManifest(
            manifest_id="wm_pending",
            manifest_hash="",
            job_id=job_id,
            run_id=run_id,
            generation=generation,
            parent_manifest_id=parent_manifest_id,
            source_host_id=source_host_id,
            source_worker_session_id=source_worker_session_id,
            entries=sorted(entries, key=lambda item: item.logical_path),
            repository=repository,
            external_data=external_data,
            portable=not reasons,
            blocked_reasons=reasons,
            source_paths=source_paths,
            materialization_mode=materialization_mode,
            created_at=utc_now(),
        )
        digest = workspace_manifest_hash(draft)
        return draft.model_copy(
            update={
                "manifest_id": f"wm_{digest[:32]}",
                "manifest_hash": digest,
            }
        )

    def snapshot_initial(
        self,
        *,
        job_id: str,
        run_id: str,
        paper_path: str,
        repo_path: str,
        log_path: str | None,
        source_host_id: str,
        external_data: list[ExternalDataReference],
    ) -> WorkspaceManifest:
        paper = Path(paper_path).expanduser().resolve()
        entries = [
            self._publish_entry(
                source=paper,
                logical_path="source/paper.pdf",
                role="paper",
            )
        ]

        if log_path:
            entries.append(
                self._publish_entry(
                    source=Path(log_path).expanduser().resolve(),
                    logical_path="source/external.log",
                    role="input_log",
                )
            )

        blocked_reasons: list[str] = []
        repository = inspect_repository_identity(repo_path)
        try:
            with TemporaryDirectory(
                prefix="repo-capsule-",
                dir=settings.workspace_staging_root,
            ) as raw_dir:
                capsule = create_repository_capsule(
                    repo_path=repo_path,
                    destination=Path(raw_dir) / "repository.bundle",
                )
                repository = capsule.identity
                entries.append(
                    self._publish_entry(
                        source=capsule.bundle_path,
                        logical_path="capsule/repository.bundle",
                        role="repository_bundle",
                    )
                )
        except WorkspaceNotPortableError as exc:
            blocked_reasons.append(str(exc))

        # required_worker_label 已经进入 Job requirements；manifest 只保存引用。
        return self._build_manifest(
            job_id=job_id,
            run_id=run_id,
            generation=0,
            parent_manifest_id=None,
            source_host_id=source_host_id,
            source_worker_session_id=None,
            entries=entries,
            repository=repository,
            external_data=external_data,
            blocked_reasons=blocked_reasons,
            source_paths=WorkspaceSourcePaths(
                run_dir=None,
                repo_path=str(Path(repo_path).expanduser().resolve()),
                paper_path=str(paper),
                log_path=(
                    str(Path(log_path).expanduser().resolve())
                    if log_path
                    else None
                ),
            ),
        )

    def snapshot_initial_from_resources(
        self,
        *,
        job_id: str,
        run_id: str,
        paper_resource,
        repo_resource,
        log_path: str | None,
        source_host_id: str,
        external_data: list[ExternalDataReference],
    ) -> WorkspaceManifest:
        """Phase 29：从 published Resource 直接构建 workspace manifest。

        直接引用同一 Blob object_key，避免再次上传内容。
        Resource 内容身份（sha256）已是最终身份，无需重新发布。
        """

        from app.resources.materializer import (
            resolved_resource_workspace_entry,
        )

        entries: list[WorkspaceBlobEntry] = []
        if paper_resource is not None:
            entries.append(
                resolved_resource_workspace_entry(
                    resolved=paper_resource
                )
            )
        else:
            raise WorkspaceIntegrityError(
                "resource-based snapshot 必须提供 paper_resource"
            )

        if log_path:
            entries.append(
                self._publish_entry(
                    source=Path(log_path).expanduser().resolve(),
                    logical_path="source/external.log",
                    role="input_log",
                )
            )

        blocked_reasons: list[str] = []
        if repo_resource is not None:
            entries.append(
                resolved_resource_workspace_entry(
                    resolved=repo_resource
                )
            )
            repository = RepositoryIdentity(
                commit_sha=(
                    repo_resource.git_commit
                    or "0" * 40
                ),
                branch="acquired",
                clean=True,
                bundle_logical_path="capsule/repository.bundle",
                has_submodules=False,
                has_lfs=False,
            )
        else:
            raise WorkspaceIntegrityError(
                "resource-based snapshot 必须提供 repo_resource"
            )

        # Resource-based manifest 引用共享 Blob。
        # 若 blob store 是 host-local，manifest 仍非 portable，需要 source_paths
        # 以便同 affinity host 复用；这里用 object_key 作为 host-local 引用标记。
        source_paths = WorkspaceSourcePaths(
            run_dir=None,
            repo_path=(
                repo_resource.object_key
                if repo_resource is not None
                else "resource://repo"
            ),
            paper_path=(
                paper_resource.object_key
                if paper_resource is not None
                else "resource://paper"
            ),
            log_path=(
                str(Path(log_path).expanduser().resolve())
                if log_path
                else None
            ),
        )
        return self._build_manifest(
            job_id=job_id,
            run_id=run_id,
            generation=0,
            parent_manifest_id=None,
            source_host_id=source_host_id,
            source_worker_session_id=None,
            entries=entries,
            repository=repository,
            external_data=external_data,
            blocked_reasons=blocked_reasons,
            source_paths=source_paths,
        )

    def derive_initial(
        self,
        *,
        job_id: str,
        run_id: str,
        parent: WorkspaceManifest,
        source_host_id: str,
        external_data: list[ExternalDataReference],
    ) -> WorkspaceManifest:
        """从父终态 Manifest 的不可变输入 Blob 创建子 generation-0。"""

        from app.workspace.repository import validate_manifest_hash

        validate_manifest_hash(parent)
        if parent.repository.clean is not True:
            raise WorkspaceNotPortableError(
                "dirty repository 不能进行不可变重跑派生"
            )
        if parent.repository.bundle_logical_path is None:
            raise WorkspaceNotPortableError(
                "父 Workspace 缺少 repository bundle identity"
            )
        if external_data != parent.external_data:
            raise WorkspaceIntegrityError(
                "派生 Job 的 dataset references 与父 Workspace 不一致"
            )

        input_roles = {
            "paper",
            "input_log",
            "repository_bundle",
        }
        entries = [
            item.model_copy(deep=True)
            for item in parent.entries
            if item.role in input_roles
        ]
        paper_count = sum(item.role == "paper" for item in entries)
        bundle_count = sum(
            item.role == "repository_bundle" for item in entries
        )
        if paper_count != 1 or bundle_count != 1:
            raise WorkspaceIntegrityError(
                "父 Workspace 必须包含唯一 paper 与 repository bundle"
            )

        # 注意：不复制 run_artifact/process_record/process_log，也不保存父 source_paths。
        return self._build_manifest(
            job_id=job_id,
            run_id=run_id,
            generation=0,
            parent_manifest_id=parent.manifest_id,
            source_host_id=source_host_id,
            source_worker_session_id=None,
            entries=entries,
            repository=parent.repository.model_copy(deep=True),
            external_data=[item.model_copy(deep=True) for item in external_data],
            blocked_reasons=[],
            source_paths=None,
            materialization_mode="blob_entries",
        )

    def _artifact_entries(
        self,
        *,
        run_root: Path,
        records: Iterable[ArtifactRecord | dict],
    ) -> list[WorkspaceBlobEntry]:
        latest: dict[str, ArtifactRecord] = {}
        for raw in records:
            record = (
                raw
                if isinstance(raw, ArtifactRecord)
                else ArtifactRecord.model_validate(raw)
            )
            latest[record.artifact_id] = record

        entries: list[WorkspaceBlobEntry] = []
        for record in latest.values():
            require_workspace_relative_path(record.relative_path)
            source = (run_root / record.relative_path).resolve()
            if run_root not in source.parents:
                raise WorkspaceIntegrityError(
                    "Artifact relative_path 逃逸 run root"
                )
            if (
                not source.is_file()
                or source.stat().st_size != record.size_bytes
                or sha256_file(source) != record.sha256
            ):
                raise WorkspaceIntegrityError(
                    f"Artifact 在 snapshot 前发生变化：{record.artifact_id}"
                )
            entries.append(
                self._publish_entry(
                    source=source,
                    logical_path=f"run/{record.relative_path}",
                    role="run_artifact",
                    executable=False,
                )
            )
        return entries

    def _process_entries(self, run_root: Path) -> list[WorkspaceBlobEntry]:
        entries: dict[str, WorkspaceBlobEntry] = {}
        for pattern in PROCESS_FILE_PATTERNS:
            for source in run_root.glob(pattern):
                if not source.is_file() or source.is_symlink():
                    continue
                relative = source.resolve().relative_to(run_root).as_posix()
                role = (
                    "process_record"
                    if source.name.endswith(".json")
                    else "process_log"
                )
                entry = self._publish_entry(
                    source=source,
                    logical_path=f"run/{relative}",
                    role=role,
                )
                entries[entry.logical_path] = entry
        return list(entries.values())

    def seal(
        self,
        *,
        job_id: str,
        run_id: str,
        run_dir: str,
        repo_path: str,
        paper_path: str,
        log_path: str | None,
        parent: WorkspaceManifest,
        source_host_id: str,
        source_worker_session_id: str,
        artifact_records: Iterable[ArtifactRecord | dict],
        external_data: list[ExternalDataReference],
        blocked_reasons: list[str],
    ) -> WorkspaceManifest:
        run_root = require_managed_run_root(run_dir)
        entries = [
            item
            for item in parent.entries
            if item.role in {
                "paper",
                "input_log",
                "repository_bundle",
            }
        ]
        entries.extend(
            self._artifact_entries(
                run_root=run_root,
                records=artifact_records,
            )
        )
        entries.extend(self._process_entries(run_root))

        repository = parent.repository
        try:
            with TemporaryDirectory(
                prefix="repo-seal-",
                dir=settings.workspace_staging_root,
            ) as raw_dir:
                capsule = create_repository_capsule(
                    repo_path=repo_path,
                    destination=Path(raw_dir) / "repository.bundle",
                )
                repository = capsule.identity
                entries = [
                    item
                    for item in entries
                    if item.role != "repository_bundle"
                ]
                entries.append(
                    self._publish_entry(
                        source=capsule.bundle_path,
                        logical_path="capsule/repository.bundle",
                        role="repository_bundle",
                    )
                )
        except WorkspaceNotPortableError as exc:
            blocked_reasons.append(str(exc))
            repository = inspect_repository_identity(repo_path)

        # 同一路径只保留最后一个内容版本。
        unique = {item.logical_path: item for item in entries}
        return self._build_manifest(
            job_id=job_id,
            run_id=run_id,
            generation=parent.generation + 1,
            parent_manifest_id=parent.manifest_id,
            source_host_id=source_host_id,
            source_worker_session_id=source_worker_session_id,
            entries=list(unique.values()),
            repository=repository,
            external_data=external_data,
            blocked_reasons=blocked_reasons,
            source_paths=WorkspaceSourcePaths(
                run_dir=str(run_root),
                repo_path=str(Path(repo_path).expanduser().resolve()),
                paper_path=str(Path(paper_path).expanduser().resolve()),
                log_path=(
                    str(Path(log_path).expanduser().resolve())
                    if log_path
                    else None
                ),
            ),
        )
