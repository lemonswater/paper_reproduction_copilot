# app/run_evidence/reader.py
from __future__ import annotations

import hashlib
import json
from typing import Protocol

from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceLimitExceededError,
    RunEvidenceNotFoundError,
)
from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import (
    TERMINAL_JOB_STATUSES,
    JobRecord,
)
from app.run_evidence.schemas import VerifiedRunEvidence
from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.repository import validate_manifest_hash
from app.workspace.schemas import WorkspaceManifest

RUN_MANIFEST_PATH = "reports/run_manifest.json"


class RunEvidenceJobReader(Protocol):
    def get(self, job_id: str) -> JobRecord:
        ...

    def get_workspace_manifest(
        self,
        manifest_id: str,
    ) -> WorkspaceManifest:
        ...


class VerifiedRunEvidenceReader:
    """统一校验 Job、Workspace、Catalog、Descriptor 和 Blob。"""

    def __init__(
        self,
        *,
        jobs: RunEvidenceJobReader,
        artifact_catalog: ArtifactCatalog,
        max_manifest_bytes: int,
        max_artifacts: int,
    ) -> None:
        self.jobs = jobs
        self.artifact_catalog = artifact_catalog
        self.max_manifest_bytes = max_manifest_bytes
        self.max_artifacts = max_artifacts

    @staticmethod
    def _require_terminal(job: JobRecord) -> None:
        if job.status not in TERMINAL_JOB_STATUSES:
            raise RunEvidenceConflictError(
                f"Job {job.job_id} 尚未终止，当前状态为 {job.status}"
            )

    @staticmethod
    def _validate_workspace(
        job: JobRecord,
        manifest: WorkspaceManifest,
    ) -> None:
        try:
            validate_manifest_hash(manifest)
        except WorkspaceIntegrityError as exc:
            raise RunEvidenceIntegrityError(
                "Workspace Manifest hash 校验失败"
            ) from exc
        if manifest.manifest_id != job.workspace_manifest_id:
            raise RunEvidenceIntegrityError(
                "Job 的 workspace_manifest_id 已漂移"
            )
        if manifest.job_id != job.job_id or manifest.run_id != job.run_id:
            raise RunEvidenceIntegrityError(
                "WorkspaceManifest 与 Job 身份不一致"
            )
        if manifest.generation != job.workspace_manifest_generation:
            raise RunEvidenceIntegrityError(
                "WorkspaceManifest generation 不一致"
            )

    def _list_artifacts(self, job: JobRecord) -> list[ArtifactView]:
        views = self.artifact_catalog.list_views(job)
        if len(views) > self.max_artifacts:
            raise RunEvidenceLimitExceededError(
                "Artifact 数量超过可信读取上限"
            )
        ids = [item.artifact_id for item in views]
        paths = [item.relative_path for item in views]
        if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
            raise RunEvidenceIntegrityError(
                "Artifact identity 或 relative_path 重复"
            )
        if any(item.run_id != job.run_id for item in views):
            raise RunEvidenceIntegrityError(
                "Artifact Catalog 混入其他 run_id"
            )
        return sorted(views, key=lambda item: item.relative_path)

    def _read_manifest_blob(
        self,
        *,
        job: JobRecord,
        views: list[ArtifactView],
    ) -> tuple[ArtifactView, dict]:
        matches = [
            item
            for item in views
            if item.relative_path == RUN_MANIFEST_PATH
        ]
        if len(matches) != 1:
            raise RunEvidenceNotFoundError(
                f"Job {job.job_id} 必须且只能有一个 {RUN_MANIFEST_PATH}"
            )
        view = matches[0]
        if view.size_bytes > self.max_manifest_bytes:
            raise RunEvidenceLimitExceededError(
                "run_manifest.json 超过读取上限"
            )

        opened = self.artifact_catalog.open(
            job=job,
            artifact_id=view.artifact_id,
        )
        try:
            descriptor = opened.artifact.descriptor
            stat = opened.blob.stat
            identity_matches = (
                descriptor.artifact_id == view.artifact_id
                and descriptor.relative_path == view.relative_path
                and descriptor.run_id == job.run_id
                and descriptor.sha256 == view.sha256
                and descriptor.size_bytes == view.size_bytes
                and stat.sha256 == view.sha256
                and stat.size_bytes == view.size_bytes
            )
            if not identity_matches:
                raise RunEvidenceIntegrityError(
                    "Catalog、Descriptor 与 Blob 身份不一致"
                )
            raw = opened.blob.body.read(self.max_manifest_bytes + 1)
        finally:
            opened.blob.body.close()

        if len(raw) > self.max_manifest_bytes or len(raw) != view.size_bytes:
            raise RunEvidenceIntegrityError(
                "run_manifest.json 读取大小不一致"
            )
        if hashlib.sha256(raw).hexdigest() != view.sha256:
            raise RunEvidenceIntegrityError(
                "run_manifest.json SHA-256 校验失败"
            )
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunEvidenceIntegrityError(
                "run_manifest.json 不是有效 UTF-8 JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise RunEvidenceConflictError(
                "run_manifest.json 顶层必须是 object"
            )
        version = payload.get("manifest_version")
        if not isinstance(version, int) or version < 4:
            raise RunEvidenceConflictError(
                "可信运行读取需要 manifest_version >= 4"
            )
        if payload.get("job_id") != job.job_id:
            raise RunEvidenceIntegrityError(
                "run_manifest.json job_id 不一致"
            )
        if payload.get("run_id") != job.run_id:
            raise RunEvidenceIntegrityError(
                "run_manifest.json run_id 不一致"
            )
        return view, payload

    def read(self, job_id: str) -> VerifiedRunEvidence:
        job = self.jobs.get(job_id)
        self._require_terminal(job)
        workspace = self.jobs.get_workspace_manifest(
            job.workspace_manifest_id
        )
        self._validate_workspace(job, workspace)
        artifacts = self._list_artifacts(job)
        manifest_view, payload = self._read_manifest_blob(
            job=job,
            views=artifacts,
        )
        return VerifiedRunEvidence(
            job=job,
            workspace=workspace,
            artifacts=tuple(artifacts),
            run_manifest_artifact=manifest_view,
            run_manifest=payload,
        )
