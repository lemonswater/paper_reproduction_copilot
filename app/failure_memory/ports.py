from __future__ import annotations

from typing import Protocol

from app.failure_memory.schemas import FailureCaseRecord


class FailureCaseRepository(Protocol):
    def initialize(self) -> None: ...

    def ping(self) -> None: ...

    def get(self, case_id: str) -> FailureCaseRecord: ...

    def find_by_source_job(
        self,
        source_job_id: str,
    ) -> FailureCaseRecord | None: ...

    def find_replay(
        self,
        *,
        operation_key: str,
        request_hash: str,
    ) -> FailureCaseRecord | None: ...

    def create(
        self,
        *,
        record: FailureCaseRecord,
        operation_key: str,
        request_hash: str,
    ) -> FailureCaseRecord: ...

    def replace(
        self,
        *,
        record: FailureCaseRecord,
        expected_version: int,
        expected_case_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> FailureCaseRecord: ...

    def list_candidates(
        self,
        *,
        stage: str,
        code: str,
        limit: int,
    ) -> list[FailureCaseRecord]: ...

    def list_records(
        self,
        *,
        include_deprecated: bool,
        limit: int,
    ) -> list[FailureCaseRecord]: ...

    def active_referenced_job_ids(self) -> set[str]: ...
