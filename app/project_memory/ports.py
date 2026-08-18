from __future__ import annotations

from typing import Protocol

from app.project_memory.schemas import (
    ProjectFactCorrectionResponse,
    ProjectFactRecord,
    ProjectJobBinding,
    ProjectRecord,
)


class ProjectMemoryRepository(Protocol):
    def initialize(self) -> None: ...
    def ping(self) -> None: ...

    def create_project(
        self,
        *,
        project: ProjectRecord,
        anchor_binding: ProjectJobBinding,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectRecord, bool]: ...

    def get_project(self, project_id: str) -> ProjectRecord: ...
    def list_projects(
        self, *, include_archived: bool, limit: int
    ) -> list[ProjectRecord]: ...

    def archive_project(
        self,
        *,
        project: ProjectRecord,
        expected_version: int,
        expected_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectRecord, bool]: ...

    def bind_job(
        self,
        *,
        binding: ProjectJobBinding,
        expected_project_version: int,
        expected_project_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectJobBinding, bool]: ...

    def project_for_job(self, job_id: str) -> ProjectRecord | None: ...
    def list_bindings(self, project_id: str) -> list[ProjectJobBinding]: ...

    def create_fact(
        self,
        *,
        fact: ProjectFactRecord,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectFactRecord, bool]: ...

    def get_fact(self, fact_id: str) -> ProjectFactRecord: ...

    def list_facts(
        self,
        *,
        project_id: str,
        include_terminal: bool,
        limit: int,
    ) -> list[ProjectFactRecord]: ...

    def replace_fact(
        self,
        *,
        fact: ProjectFactRecord,
        expected_version: int,
        expected_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectFactRecord, bool]: ...

    def replace_with_successor(
        self,
        *,
        previous: ProjectFactRecord,
        successor: ProjectFactRecord,
        expected_version: int,
        expected_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> ProjectFactCorrectionResponse: ...

    def active_facts(
        self, *, project_id: str, now: str, limit: int
    ) -> list[ProjectFactRecord]: ...
    def expire_due(self, *, project_id: str, now: str, actor: str) -> int: ...
    def active_referenced_job_ids(self) -> set[str]: ...
