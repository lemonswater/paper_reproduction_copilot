from __future__ import annotations

"""Phase 29 ResourceRepository 端口。

所有状态更新都使用 ``WHERE resource_id=? AND claim_token=? AND status IN (...)``
的 fencing 条件。旧 Worker 即使稍后完成下载，也不能发布新 claim 的资源。
"""

from typing import Protocol

from app.resources.schemas import (
    ResourceApproval,
    ResourceManifest,
    ResourceRecord,
    ResourceRequest,
)


class ResourceRepository(Protocol):
    def initialize(self) -> None:
        ...

    def ping(self) -> None:
        ...

    def submit(
        self,
        *,
        resource_id: str,
        idempotency_key: str,
        request: ResourceRequest,
        request_sha256: str,
    ) -> tuple[ResourceRecord, bool]:
        ...

    def get(self, resource_id: str) -> ResourceRecord:
        ...

    def approve(
        self,
        *,
        resource_id: str,
        approval: ResourceApproval,
        expected_version: int | None,
    ) -> ResourceRecord:
        ...

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
    ) -> ResourceRecord | None:
        ...

    def heartbeat(
        self,
        *,
        resource_id: str,
        claim_token: str,
        lease_seconds: float,
    ) -> ResourceRecord:
        ...

    def mark_validating(
        self,
        *,
        resource_id: str,
        claim_token: str,
    ) -> ResourceRecord:
        ...

    def mark_published(
        self,
        *,
        resource_id: str,
        claim_token: str,
        manifest: ResourceManifest,
    ) -> ResourceRecord:
        ...

    def mark_failed(
        self,
        *,
        resource_id: str,
        claim_token: str,
        error: dict,
        retryable: bool,
    ) -> ResourceRecord:
        ...

    def request_cancel(
        self,
        *,
        resource_id: str,
        reason: str,
        actor: str,
        expected_version: int | None,
    ) -> ResourceRecord:
        ...

    def list_expired_fetching(
        self, *, limit: int = 100
    ) -> list[ResourceRecord]:
        ...

    def requeue_expired(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        ...

    def require_reconciliation(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        ...

    def list_events(
        self,
        resource_id: str,
        *,
        limit: int = 200,
    ) -> list:
        ...
