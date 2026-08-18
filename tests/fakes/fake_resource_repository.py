"""Phase 29 Fake ResourceRepository for offline tests.

内存实现，支持 lease/heartbeat/fencing 语义，用于 Worker/reconcile/API
单元测试，不依赖 SQLite 或 PostgreSQL。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.resources.errors import (
    ResourceConflictError,
    ResourceNotFoundError,
    ResourceStateAmbiguous,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceEvent,
    ResourceManifest,
    ResourceRecord,
    ResourceRequest,
    TERMINAL_RESOURCE_STATUSES,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class _StoredResource:
    record: ResourceRecord
    claim_token_hash: str | None = None
    lease_expires_ts: float | None = None
    events: list[ResourceEvent] = field(default_factory=list)
    _next_event_id: int = 1


class FakeResourceRepository:
    """内存 ResourceRepository，用于离线测试。"""

    def __init__(self):
        self._store: dict[str, _StoredResource] = {}
        self._by_idempotency: dict[str, str] = {}
        self._clock: float | None = None
        # 暴露最近一次 claim 返回的明文 token，方便测试模拟 lease loss。
        self.last_claim_token: str | None = None

    def initialize(self) -> None:
        pass

    def ping(self) -> None:
        pass

    def _now(self) -> float:
        return self._clock if self._clock is not None else time.time()

    def set_clock(self, ts: float | None) -> None:
        self._clock = ts

    def advance_clock(self, seconds: float) -> None:
        if self._clock is None:
            self._clock = time.time()
        self._clock += seconds

    def _append_event(
        self,
        stored: _StoredResource,
        *,
        event_type: str,
        actor: str,
        payload: dict,
    ) -> None:
        event = ResourceEvent(
            event_id=stored._next_event_id,
            resource_id=stored.record.resource_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            created_at=_utc_now(),
        )
        stored._next_event_id += 1
        stored.events.append(event)

    def submit(
        self,
        *,
        resource_id: str,
        idempotency_key: str,
        request: ResourceRequest,
        request_sha256: str,
    ) -> tuple[ResourceRecord, bool]:
        existing_id = self._by_idempotency.get(idempotency_key)
        if existing_id is not None:
            stored = self._store[existing_id]
            if stored.record.request_sha256 != request_sha256:
                raise ResourceConflictError(
                    "idempotency_key 已绑定不同 request"
                )
            return stored.record, False
        now = _utc_now()
        record = ResourceRecord(
            resource_id=resource_id,
            idempotency_key=idempotency_key,
            request=request,
            request_sha256=request_sha256,
            approval=None,
            status="awaiting_approval",
            version=0,
            attempt_count=0,
            worker_id=None,
            claim_token=None,
            heartbeat_at=None,
            lease_expires_at=None,
            manifest=None,
            error=None,
            created_at=now,
            updated_at=now,
        )
        stored = _StoredResource(record=record)
        self._store[resource_id] = stored
        self._by_idempotency[idempotency_key] = resource_id
        self._append_event(
            stored,
            event_type="resource_submitted",
            actor="api",
            payload={
                "kind": request.kind,
                "request_sha256": request_sha256,
            },
        )
        return record, True

    def get(self, resource_id: str) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        return stored.record

    def approve(
        self,
        *,
        resource_id: str,
        approval: ResourceApproval,
        expected_version: int | None,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        record = stored.record
        if (
            expected_version is not None
            and record.version != expected_version
        ):
            raise ResourceConflictError("resource version 冲突")
        if record.status not in {"awaiting_approval", "rejected"}:
            raise ResourceConflictError(
                f"resource 状态 {record.status} 不可审批"
            )
        new_status = (
            "queued"
            if approval.decision == "approved"
            else "rejected"
        )
        record = record.model_copy(
            update={
                "approval": approval,
                "status": new_status,
                "version": record.version + 1,
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        self._append_event(
            stored,
            event_type=f"resource_{approval.decision}",
            actor=approval.decided_by,
            payload={
                "decision": approval.decision,
                "request_sha256": approval.request_sha256,
            },
        )
        return record

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
    ) -> ResourceRecord | None:
        now = self._now()
        candidates = [
            s
            for s in self._store.values()
            if s.record.status == "queued"
        ]
        candidates.sort(
            key=lambda s: s.record.created_at
        )
        for stored in candidates:
            token = f"rclaim_{uuid4().hex}"
            self.last_claim_token = token
            lease_expires = now + lease_seconds
            record = stored.record.model_copy(
                update={
                    "status": "fetching",
                    "version": stored.record.version + 1,
                    "attempt_count": (
                        stored.record.attempt_count + 1
                    ),
                    "worker_id": worker_id,
                    "claim_token": token,
                    "heartbeat_at": _utc_now(),
                    "lease_expires_at": datetime.fromtimestamp(
                        lease_expires, tz=timezone.utc
                    ).isoformat(),
                    "error": None,
                    "updated_at": _utc_now(),
                }
            )
            stored.record = record
            stored.claim_token_hash = _hash_token(token)
            stored.lease_expires_ts = lease_expires
            self._append_event(
                stored,
                event_type="resource_claimed",
                actor=worker_id,
                payload={
                    "claim_token_suffix": token[-12:],
                },
            )
            return record
        return None

    def heartbeat(
        self,
        *,
        resource_id: str,
        claim_token: str,
        lease_seconds: float,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        if (
            stored.claim_token_hash != _hash_token(claim_token)
            or stored.record.status != "fetching"
        ):
            raise ResourceStateAmbiguous(
                "heartbeat 失败：claim 已失效或状态非 fetching"
            )
        now = self._now()
        lease_expires = now + lease_seconds
        record = stored.record.model_copy(
            update={
                "heartbeat_at": _utc_now(),
                "lease_expires_at": datetime.fromtimestamp(
                    lease_expires, tz=timezone.utc
                ).isoformat(),
                "claim_token": claim_token,
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        stored.lease_expires_ts = lease_expires
        return record

    def mark_validating(
        self,
        *,
        resource_id: str,
        claim_token: str,
    ) -> ResourceRecord:
        return self._fenced(
            resource_id=resource_id,
            claim_token=claim_token,
            from_statuses={"fetching"},
            to_status="validating",
            event_type="resource_validating",
        )

    def mark_published(
        self,
        *,
        resource_id: str,
        claim_token: str,
        manifest: ResourceManifest,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        if (
            stored.claim_token_hash != _hash_token(claim_token)
            or stored.record.status != "validating"
        ):
            raise ResourceStateAmbiguous(
                "mark_published 失败"
            )
        record = stored.record.model_copy(
            update={
                "status": "published",
                "version": stored.record.version + 1,
                "manifest": manifest,
                "worker_id": None,
                "claim_token": None,
                "heartbeat_at": None,
                "lease_expires_at": None,
                "error": None,
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        stored.claim_token_hash = None
        stored.lease_expires_ts = None
        self._append_event(
            stored,
            event_type="resource_published",
            actor="resource_worker",
            payload={
                "manifest_sha256": manifest.manifest_sha256,
                "object_key": manifest.object_key,
            },
        )
        return record

    def mark_failed(
        self,
        *,
        resource_id: str,
        claim_token: str,
        error: dict,
        retryable: bool,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        if (
            stored.claim_token_hash != _hash_token(claim_token)
            or stored.record.status
            not in {"fetching", "validating"}
        ):
            raise ResourceStateAmbiguous(
                "mark_failed 失败"
            )
        new_status = (
            "failed_retryable" if retryable else "failed_terminal"
        )
        record = stored.record.model_copy(
            update={
                "status": new_status,
                "version": stored.record.version + 1,
                "worker_id": None,
                "claim_token": None,
                "heartbeat_at": None,
                "lease_expires_at": None,
                "error": error,
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        stored.claim_token_hash = None
        stored.lease_expires_ts = None
        self._append_event(
            stored,
            event_type=f"resource_{new_status}",
            actor="resource_worker",
            payload={
                "error_category": error.get("category"),
                "retryable": retryable,
            },
        )
        return record

    def request_cancel(
        self,
        *,
        resource_id: str,
        reason: str,
        actor: str,
        expected_version: int | None,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        record = stored.record
        if (
            expected_version is not None
            and record.version != expected_version
        ):
            raise ResourceConflictError("resource version 冲突")
        if record.status in TERMINAL_RESOURCE_STATUSES:
            raise ResourceConflictError(
                f"resource 已终态：{record.status}"
            )
        record = record.model_copy(
            update={
                "status": "cancelled",
                "version": record.version + 1,
                "worker_id": None,
                "claim_token": None,
                "heartbeat_at": None,
                "lease_expires_at": None,
                "error": {"reason": reason, "actor": actor},
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        stored.claim_token_hash = None
        stored.lease_expires_ts = None
        self._append_event(
            stored,
            event_type="resource_cancelled",
            actor=actor,
            payload={"reason": reason},
        )
        return record

    def list_expired_fetching(
        self, *, limit: int = 100
    ) -> list[ResourceRecord]:
        now = self._now()
        expired = [
            s.record
            for s in self._store.values()
            if s.record.status == "fetching"
            and s.lease_expires_ts is not None
            and s.lease_expires_ts < now
        ]
        return expired[:limit]

    def requeue_expired(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        if (
            stored.claim_token_hash
            != _hash_token(expired_claim_token)
            or stored.record.status != "fetching"
        ):
            raise ResourceStateAmbiguous(
                "requeue_expired 失败"
            )
        record = stored.record.model_copy(
            update={
                "status": "queued",
                "version": stored.record.version + 1,
                "worker_id": None,
                "claim_token": None,
                "heartbeat_at": None,
                "lease_expires_at": None,
                "error": {
                    "category": "lease_expired",
                    "detail": detail,
                },
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        stored.claim_token_hash = None
        stored.lease_expires_ts = None
        self._append_event(
            stored,
            event_type="resource_requeued",
            actor="reconciler",
            payload={"detail": detail},
        )
        return record

    def require_reconciliation(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        if (
            stored.claim_token_hash
            != _hash_token(expired_claim_token)
            or stored.record.status != "fetching"
        ):
            raise ResourceStateAmbiguous(
                "require_reconciliation 失败"
            )
        record = stored.record.model_copy(
            update={
                "status": "reconciliation_required",
                "version": stored.record.version + 1,
                "error": {
                    "category": "lease_ambiguous",
                    "detail": detail,
                },
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        self._append_event(
            stored,
            event_type="resource_reconciliation_required",
            actor="reconciler",
            payload={"detail": detail},
        )
        return record

    def list_events(
        self,
        resource_id: str,
        *,
        limit: int = 200,
    ) -> list[ResourceEvent]:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        return list(reversed(stored.events))[:limit]

    def _fenced(
        self,
        *,
        resource_id: str,
        claim_token: str,
        from_statuses: set[str],
        to_status: str,
        event_type: str,
    ) -> ResourceRecord:
        stored = self._store.get(resource_id)
        if stored is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        if (
            stored.claim_token_hash != _hash_token(claim_token)
            or stored.record.status not in from_statuses
        ):
            raise ResourceStateAmbiguous(
                f"fenced transition 到 {to_status} 失败"
            )
        record = stored.record.model_copy(
            update={
                "status": to_status,
                "version": stored.record.version + 1,
                "claim_token": claim_token,
                "updated_at": _utc_now(),
            }
        )
        stored.record = record
        self._append_event(
            stored,
            event_type=event_type,
            actor="resource_worker",
            payload={"to_status": to_status},
        )
        return record
