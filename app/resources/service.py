from __future__ import annotations

"""Phase 29 ResourceService。

CLI/API 共用的用例层，不直接执行 SQL。负责：
- 生成 resource_id 与 request hash；
- 提交/审批/取消；
- 把内部 ResourceRecord 投影成公开视图（不暴露 claim_token、原始 URL query）。
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.observability.context import (
    bind_telemetry_context,
)
from app.observability.instrumentation import (
    increment_counter_safe,
)
from app.observability.ports import TelemetryPort
from app.observability.runtime import (
    build_telemetry_runtime,
)
from app.resources.ports import ResourceRepository
from app.resources.request_hash import (
    canonicalize_url,
    resource_request_sha256,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceEvent,
    ResourceRecord,
    ResourceRequest,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResourceService:
    def __init__(
        self,
        repository: ResourceRepository,
        *,
        telemetry: TelemetryPort | None = None,
    ):
        self.repository = repository
        self.repository.initialize()
        self.telemetry = (
            telemetry
            if telemetry is not None
            else build_telemetry_runtime().telemetry
        )

    def submit(
        self,
        *,
        request: ResourceRequest,
        idempotency_key: str,
    ) -> tuple[ResourceRecord, bool]:
        key = idempotency_key.strip()
        if not key or len(key) > 300:
            raise ValueError(
                "idempotency_key 长度必须为 1..300"
            )
        request_sha = resource_request_sha256(request)
        resource_id = f"res_{uuid4().hex}"
        with bind_telemetry_context(
            resource_id=resource_id
        ):
            with self.telemetry.span(
                "resource_service.submit",
                attributes={"kind": request.kind},
            ):
                try:
                    record, created = (
                        self.repository.submit(
                            resource_id=resource_id,
                            idempotency_key=key,
                            request=request,
                            request_sha256=request_sha,
                        )
                    )
                except Exception:
                    increment_counter_safe(
                        self.telemetry,
                        "paper_copilot_resources_submitted_total",
                        attributes={"outcome": "error"},
                    )
                    raise
                increment_counter_safe(
                    self.telemetry,
                    "paper_copilot_resources_submitted_total",
                    attributes={
                        "outcome": (
                            "created"
                            if created
                            else "idempotent_hit"
                        )
                    },
                )
                return record, created

    def get(self, resource_id: str) -> ResourceRecord:
        return self.repository.get(resource_id)

    def approve(
        self,
        *,
        resource_id: str,
        approval: ResourceApproval,
        expected_version: int | None = None,
    ) -> ResourceRecord:
        return self.repository.approve(
            resource_id=resource_id,
            approval=approval,
            expected_version=expected_version,
        )

    def cancel(
        self,
        *,
        resource_id: str,
        reason: str,
        actor: str = "cli",
        expected_version: int | None = None,
    ) -> ResourceRecord:
        return self.repository.request_cancel(
            resource_id=resource_id,
            reason=reason,
            actor=actor,
            expected_version=expected_version,
        )

    def events(
        self,
        resource_id: str,
        *,
        limit: int = 200,
    ) -> list[ResourceEvent]:
        # 先确认 resource 存在，避免返回空 event 列表误导。
        self.repository.get(resource_id)
        return self.repository.list_events(
            resource_id,
            limit=limit,
        )

    def list_expired_fetching(
        self, *, limit: int = 100
    ) -> list[ResourceRecord]:
        return self.repository.list_expired_fetching(
            limit=limit
        )


def sanitize_resource_view(
    record: ResourceRecord,
    *,
    reveal_source: bool = False,
) -> dict[str, Any]:
    """公开视图：默认不暴露原始 URL query/凭据，claim_token 永不返回。

    第一版 canonicalize_url 已拒绝 query/userinfo/fragment，因此
    sanitized URL 等于 canonical URL；``reveal_source`` 仅供运维排查。
    """

    request = record.request
    source_url = (
        canonicalize_url(request.source_url)
        if reveal_source
        else canonicalize_url(request.source_url)
    )
    approval_view: dict[str, Any] | None = None
    if record.approval is not None:
        approval_view = {
            "decision": record.approval.decision,
            "request_sha256": record.approval.request_sha256,
            "decided_by": record.approval.decided_by,
            "decided_at": record.approval.decided_at,
            "reason": record.approval.reason,
        }
    manifest_view: dict[str, Any] | None = None
    if record.manifest is not None:
        manifest_view = {
            "manifest_sha256": record.manifest.manifest_sha256,
            "object_key": record.manifest.object_key,
            "sha256": record.manifest.sha256,
            "size_bytes": record.manifest.size_bytes,
            "media_type": record.manifest.media_type,
            "git_commit": record.manifest.git_commit,
            "acquired_at": record.manifest.acquired_at,
            "redirect_chain_sanitized": (
                list(record.manifest.redirect_chain_sanitized)
            ),
            "source_url_sanitized": (
                record.manifest.source_url_sanitized
            ),
        }
    return {
        "resource_id": record.resource_id,
        "idempotency_key": record.idempotency_key,
        "kind": request.kind,
        "source_url_sanitized": source_url,
        "purpose": request.purpose,
        "expected_sha256": request.expected_sha256,
        "expected_git_commit": request.expected_git_commit,
        "request_sha256": record.request_sha256,
        "status": record.status,
        "version": record.version,
        "attempt_count": record.attempt_count,
        "worker_id": record.worker_id,
        "approval": approval_view,
        "manifest": manifest_view,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def build_resource_service(
    *,
    repository: ResourceRepository | None = None,
    telemetry: TelemetryPort | None = None,
) -> ResourceService:
    """CLI/API/Worker 共用 composition root。"""

    if repository is None:
        from app.resources.repository import (
            build_resource_repository,
        )

        repository = build_resource_repository()
    return ResourceService(repository, telemetry=telemetry)
