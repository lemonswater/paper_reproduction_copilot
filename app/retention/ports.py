"""Retention 窄端口定义。"""
from __future__ import annotations
from pathlib import Path
from contextlib import AbstractContextManager
from typing import Protocol
from app.job_runtime.schemas import JobRecord
from app.retention.schemas import BlobReference
from app.workspace.schemas import WorkspaceBinding, WorkspaceManifest

class JobRetentionPort(Protocol):
    def list_retention_candidates(
        self,
        *,
        updated_before: float,
        limit: int,
    ) -> list[JobRecord]: ...

    def get(self, job_id: str) -> JobRecord: ...

    def list_workspace_bindings_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceBinding]: ...

    def list_workspace_manifests_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceManifest]: ...

    def count_workspace_blob_references(
        self,
        *,
        object_key: str,
    ) -> int: ...

    def delete_job_for_retention(
        self,
        *,
        job_id: str,
        expected_version: int,
        expected_status: str,
    ) -> bool: ...

class ArtifactRetentionPort(Protocol):
    def list_blob_references_for_job(
        self,
        job_id: str,
    ) -> list[BlobReference]: ...

    def delete_job_artifacts(self, job_id: str) -> int: ...

    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int: ...

class ChatRetentionPort(Protocol):
    def delete_job_messages(self, job_id: str) -> int: ...


class NotificationRetentionPort(Protocol):
    def delete_for_job(self, job_id: str) -> int: ...


class FailureMemoryRetentionPort(Protocol):
    def active_referenced_job_ids(self) -> set[str]: ...


class ProjectMemoryRetentionPort(Protocol):
    def active_referenced_job_ids(self) -> set[str]: ...


class KnowledgeMemoryRetentionPort(Protocol):
    def active_referenced_job_ids(self) -> set[str]: ...


class McpEvidenceRetentionPort(Protocol):
    def delete_for_job(self, job_id: str) -> int: ...


class McpExportAuditRetentionPort(Protocol):
    def delete_for_job(self, job_id: str) -> int: ...


class ResourceReferencePort(Protocol):
    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int: ...

class CheckpointRetentionPort(Protocol):
    def delete_thread(self, thread_id: str) -> None: ...

class DeletableBlobStore(Protocol):
    backend_name: str
    def delete_if_matches(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_size: int,
    ) -> bool: ...

class PathRemover(Protocol):
    def validate_job_paths(
        self,
        *,
        job: JobRecord,
        bindings: list[WorkspaceBinding],
    ) -> list[Path]: ...

    def remove_tree(self, path: Path) -> int: ...

class SweepLock(Protocol):
    def acquire(self) -> AbstractContextManager[None]: ...
