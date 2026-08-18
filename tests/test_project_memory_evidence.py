"""Phase 46: Project Memory Evidence Reader 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.project_memory.errors import ProjectMemoryConflictError, ProjectMemoryIntegrityError
from app.project_memory.evidence import (
    ProjectChatEvidenceReader,
    ProjectJobEvidenceReader,
    chat_message_sha256,
)
from app.project_memory.schemas import ProjectAnchor
from app.workspace.repository import workspace_manifest_hash
from app.workspace.schemas import (
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)
from tests.helpers.project_memory import NOW


def _make_manifest(
    *,
    job_id: str = "job-001",
    run_id: str = "run-001",
    manifest_id: str = "manifest-001",
    paper_sha256: str = "b" * 64,
    commit: str = "c" * 40,
    generation: int = 0,
) -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_id=manifest_id,
        manifest_hash="0" * 64,
        job_id=job_id,
        run_id=run_id,
        generation=generation,
        source_host_id="host-001",
        entries=[
            WorkspaceBlobEntry(
                role="paper",
                logical_path="paper.pdf",
                object_key="blob-paper",
                sha256=paper_sha256,
                size_bytes=1024,
            ),
            WorkspaceBlobEntry(
                role="repository_bundle",
                logical_path="repo.zip",
                object_key="blob-repo",
                sha256="d" * 64,
                size_bytes=2048,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha=commit,
            branch="main",
            clean=True,
        ),
        portable=True,
        created_at=NOW,
    )
    payload = draft.model_dump(mode="json")
    payload["manifest_hash"] = workspace_manifest_hash(draft)
    return WorkspaceManifest.model_validate(payload)

def test_job_evidence_reader_returns_anchor():
    manifest = _make_manifest()
    job = MagicMock()
    job.job_id = "job-001"
    job.version = 0
    job.run_id = "run-001"
    job.workspace_manifest_id = "manifest-001"
    job.workspace_manifest_generation = 0

    jobs = MagicMock()
    jobs.get.return_value = job
    jobs.store.get_workspace_manifest.return_value = manifest

    reader = ProjectJobEvidenceReader(jobs)
    snapshot = reader.read("job-001")
    assert isinstance(snapshot.anchor, ProjectAnchor)
    assert snapshot.anchor.job_id == "job-001"
    assert snapshot.anchor.paper_sha256 == "b" * 64
    assert snapshot.anchor.repository_commit == "c" * 40


def test_job_evidence_reader_fails_on_manifest_job_mismatch():
    manifest = _make_manifest(job_id="other-job")
    job = MagicMock()
    job.job_id = "job-001"
    job.version = 0
    job.run_id = "run-001"
    job.workspace_manifest_id = "manifest-001"
    job.workspace_manifest_generation = 0

    jobs = MagicMock()
    jobs.get.return_value = job
    jobs.store.get_workspace_manifest.return_value = manifest

    reader = ProjectJobEvidenceReader(jobs)
    with pytest.raises(ProjectMemoryIntegrityError):
        reader.read("job-001")


def test_job_evidence_reader_fails_on_generation_mismatch():
    manifest = _make_manifest(generation=1)
    job = MagicMock()
    job.job_id = "job-001"
    job.version = 0
    job.run_id = "run-001"
    job.workspace_manifest_id = "manifest-001"
    job.workspace_manifest_generation = 0

    jobs = MagicMock()
    jobs.get.return_value = job
    jobs.store.get_workspace_manifest.return_value = manifest

    reader = ProjectJobEvidenceReader(jobs)
    with pytest.raises(ProjectMemoryConflictError):
        reader.read("job-001")


def test_chat_evidence_reader_returns_message():
    message = MagicMock()
    message.message_id = "msg-001"
    message.job_id = "job-001"
    message.sequence = 3
    message.role = "user"
    message.content = "some user text"
    message.created_at = NOW

    repo = MagicMock()
    repo.list_messages_range.return_value = [message]

    reader = ProjectChatEvidenceReader(repo)
    result = reader.message_at(job_id="job-001", sequence=3)
    assert result.sequence == 3
    assert result.role == "user"


def test_chat_evidence_reader_rejects_missing_sequence():
    repo = MagicMock()
    repo.list_messages_range.return_value = []

    reader = ProjectChatEvidenceReader(repo)
    with pytest.raises(ProjectMemoryConflictError):
        reader.message_at(job_id="job-001", sequence=99)


def test_chat_message_sha256_includes_role_and_identity():
    message = MagicMock()
    message.message_id = "msg-001"
    message.job_id = "job-001"
    message.sequence = 1
    message.role = "user"
    message.content = "hello"
    message.created_at = NOW

    hash_user = chat_message_sha256(message)

    message.role = "assistant"
    hash_assistant = chat_message_sha256(message)

    assert hash_user != hash_assistant


def test_chat_message_sha256_changes_with_content():
    message = MagicMock()
    message.message_id = "msg-001"
    message.job_id = "job-001"
    message.sequence = 1
    message.role = "user"
    message.content = "hello"
    message.created_at = NOW

    hash1 = chat_message_sha256(message)

    message.content = "goodbye"
    hash2 = chat_message_sha256(message)

    assert hash1 != hash2
