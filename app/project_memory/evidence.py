from __future__ import annotations

from dataclasses import dataclass

from app.chat.store import ChatRepository
from app.job_runtime.service import JobService
from app.project_memory.errors import (
    ProjectMemoryConflictError,
    ProjectMemoryIntegrityError,
)
from app.project_memory.identity import canonical_sha256
from app.project_memory.schemas import ProjectAnchor
from app.workspace.repository import validate_manifest_hash
from app.workspace.schemas import WorkspaceManifest


def _paper_sha256(manifest: WorkspaceManifest) -> str:
    papers = [item for item in manifest.entries if item.role == "paper"]
    if len(papers) != 1:
        raise ProjectMemoryIntegrityError(
            "Workspace Manifest 必须包含唯一 paper entry"
        )
    return papers[0].sha256


@dataclass(frozen=True)
class ProjectJobSnapshot:
    anchor: ProjectAnchor


class ProjectJobEvidenceReader:
    def __init__(self, jobs: JobService) -> None:
        self.jobs = jobs

    def read(self, job_id: str) -> ProjectJobSnapshot:
        job = self.jobs.get(job_id)
        manifest = self.jobs.store.get_workspace_manifest(
            job.workspace_manifest_id
        )
        validate_manifest_hash(manifest)

        # Job pointer 与 Manifest 自身身份必须一致，不能只信其中一边。
        if manifest.job_id != job.job_id or manifest.run_id != job.run_id:
            raise ProjectMemoryIntegrityError("Job 与 Workspace Manifest 身份不一致")
        if manifest.manifest_id != job.workspace_manifest_id:
            raise ProjectMemoryIntegrityError("Job manifest pointer 已漂移")
        if manifest.generation != job.workspace_manifest_generation:
            raise ProjectMemoryConflictError("Workspace generation 已变化")

        return ProjectJobSnapshot(
            anchor=ProjectAnchor(
                job_id=job.job_id,
                job_version=job.version,
                run_id=job.run_id,
                workspace_manifest_id=manifest.manifest_id,
                workspace_manifest_hash=manifest.manifest_hash,
                paper_sha256=_paper_sha256(manifest),
                repository_commit=manifest.repository.commit_sha,
                repository_clean=manifest.repository.clean,
            )
        )


class ProjectChatEvidenceReader:
    def __init__(self, repository: ChatRepository) -> None:
        self.repository = repository

    def message_at(self, *, job_id: str, sequence: int):
        rows = self.repository.list_messages_range(
            job_id=job_id,
            start_sequence=sequence,
            end_sequence=sequence,
            limit=1,
        )
        if len(rows) != 1 or rows[0].sequence != sequence:
            raise ProjectMemoryConflictError("未找到指定 Chat message sequence")
        return rows[0]


def chat_message_sha256(message) -> str:
    # Hash 包含 role、content 和 identity；不能只 Hash 文本。
    return canonical_sha256(
        {
            "message_id": message.message_id,
            "job_id": message.job_id,
            "sequence": message.sequence,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        }
    )
