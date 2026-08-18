from __future__ import annotations

"""Phase 29 PostgreSQL ResourceRepository。

正式 Resource Worker 在 PostgreSQL backend 下使用，避免与 SQLite 不一致的
lease 时钟和持久化边界。表结构由 alembic migration 管理；本模块只做读写。
"""

import hashlib
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, insert

from app.observability.context import short_secret_hash
from app.persistence.database import (
    build_engine,
    database_clock,
)
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


resources = sa.Table(
    "resources",
    sa.MetaData(),
    sa.Column("resource_id", sa.Text, primary_key=True),
    sa.Column(
        "idempotency_key",
        sa.Text,
        nullable=False,
        unique=True,
    ),
    sa.Column("request_sha256", sa.Text, nullable=False),
    sa.Column("request_json", JSONB, nullable=False),
    sa.Column("approval_json", JSONB, nullable=True),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("attempt_count", sa.Integer, nullable=False),
    sa.Column("worker_id", sa.Text, nullable=True),
    sa.Column("claim_token_hash", sa.Text, nullable=True),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("manifest_json", JSONB, nullable=True),
    sa.Column("error_json", JSONB, nullable=True),
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
)

resource_events = sa.Table(
    "resource_events",
    sa.MetaData(),
    sa.Column(
        "event_id",
        sa.BigInteger,
        primary_key=True,
        autoincrement=True,
    ),
    sa.Column("resource_id", sa.Text, nullable=False),
    sa.Column("event_type", sa.Text, nullable=False),
    sa.Column("actor", sa.Text, nullable=False),
    sa.Column("payload_json", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


class PostgresResourceRepository:
    """PostgreSQL ResourceRepository；表结构由 alembic 管理。"""

    def __init__(self):
        self._engine: sa.Engine = build_engine()

    def initialize(self) -> None:
        # 表由 alembic 创建；这里只 ping。
        self.ping()

    def ping(self) -> None:
        with self._engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))

    def _row_to_record(self, row) -> ResourceRecord:
        approval_raw = row.approval_json
        approval = (
            ResourceApproval.model_validate(approval_raw)
            if approval_raw is not None
            else None
        )
        manifest_raw = row.manifest_json
        manifest = (
            ResourceManifest.model_validate(manifest_raw)
            if manifest_raw is not None
            else None
        )
        request = ResourceRequest.model_validate(
            row.request_json
        )
        return ResourceRecord(
            resource_id=row.resource_id,
            idempotency_key=row.idempotency_key,
            request=request,
            request_sha256=row.request_sha256,
            approval=approval,
            status=row.status,
            version=row.version,
            attempt_count=row.attempt_count,
            worker_id=row.worker_id,
            claim_token=None,
            heartbeat_at=(
                row.heartbeat_at.isoformat()
                if row.heartbeat_at is not None
                else None
            ),
            lease_expires_at=(
                row.lease_expires_at.isoformat()
                if row.lease_expires_at is not None
                else None
            ),
            manifest=manifest,
            error=row.error_json
            if isinstance(row.error_json, dict)
            else None,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )

    def submit(
        self,
        *,
        resource_id: str,
        idempotency_key: str,
        request: ResourceRequest,
        request_sha256: str,
    ) -> tuple[ResourceRecord, bool]:
        now = database_clock(self._engine)
        payload = request.model_dump(mode="json")
        stmt = (
            insert(resources)
            .values(
                resource_id=resource_id,
                idempotency_key=idempotency_key,
                request_sha256=request_sha256,
                request_json=payload,
                approval_json=None,
                status="awaiting_approval",
                version=0,
                attempt_count=0,
                worker_id=None,
                claim_token_hash=None,
                heartbeat_at=None,
                lease_expires_at=None,
                manifest_json=None,
                error_json=None,
                available_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=["idempotency_key"]
            )
        )
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
            if result.rowcount == 0:
                existing = conn.execute(
                    sa.select(resources).where(
                        resources.c.idempotency_key
                        == idempotency_key
                    )
                ).one()
                if (
                    existing.request_sha256
                    != request_sha256
                ):
                    raise ResourceConflictError(
                        "idempotency_key 已绑定不同 request"
                    )
                conn.execute(
                    resource_events.insert().values(
                        resource_id=existing.resource_id,
                        event_type="resource_submit_idempotent",
                        actor="api",
                        payload_json={
                            "request_sha256": request_sha256
                        },
                        created_at=now,
                    )
                )
                return self._row_to_record(existing), False
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type="resource_submitted",
                    actor="api",
                    payload_json={
                        "kind": request.kind,
                        "request_sha256": request_sha256,
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row), True

    def get(self, resource_id: str) -> ResourceRecord:
        with self._engine.connect() as conn:
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).first()
        if row is None:
            raise ResourceNotFoundError(
                f"resource 不存在：{resource_id}"
            )
        return self._row_to_record(row)

    def approve(
        self,
        *,
        resource_id: str,
        approval: ResourceApproval,
        expected_version: int | None,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        new_status = (
            "queued"
            if approval.decision == "approved"
            else "rejected"
        )
        with self._engine.begin() as conn:
            row = conn.execute(
                sa.select(resources)
                .where(resources.c.resource_id == resource_id)
                .with_for_update()
            ).first()
            if row is None:
                raise ResourceNotFoundError(
                    f"resource 不存在：{resource_id}"
                )
            if (
                expected_version is not None
                and row.version != expected_version
            ):
                raise ResourceConflictError(
                    "resource version 冲突"
                )
            if row.status not in {
                "awaiting_approval",
                "rejected",
            }:
                raise ResourceConflictError(
                    f"resource 状态 {row.status} 不可审批"
                )
            updated = conn.execute(
                sa.update(resources)
                .values(
                    approval_json=approval.model_dump(
                        mode="json"
                    ),
                    status=new_status,
                    version=resources.c.version + 1,
                    available_at=(
                        now
                        if new_status == "queued"
                        else row.available_at
                    ),
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.status.in_(
                        ["awaiting_approval", "rejected"]
                    ),
                )
            )
            if updated.rowcount != 1:
                raise ResourceConflictError(
                    "approve 竞争失败"
                )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type=f"resource_{approval.decision}",
                    actor=approval.decided_by,
                    payload_json={
                        "decision": approval.decision,
                        "request_sha256": approval.request_sha256,
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row)

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
    ) -> ResourceRecord | None:
        now = database_clock(self._engine)
        token = f"rclaim_{uuid4().hex}"
        token_hash = _hash_token(token)
        from datetime import timedelta

        lease_expires = now + timedelta(seconds=lease_seconds)
        with self._engine.begin() as conn:
            candidate = conn.execute(
                sa.select(resources)
                .where(
                    resources.c.status == "queued",
                    resources.c.available_at <= now,
                )
                .order_by(
                    resources.c.available_at.asc(),
                    resources.c.created_at.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            ).first()
            if candidate is None:
                return None
            updated = conn.execute(
                sa.update(resources)
                .values(
                    status="fetching",
                    version=resources.c.version + 1,
                    attempt_count=(
                        resources.c.attempt_count + 1
                    ),
                    worker_id=worker_id,
                    claim_token_hash=token_hash,
                    heartbeat_at=now,
                    lease_expires_at=lease_expires,
                    error_json=None,
                    available_at=now,
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id
                    == candidate.resource_id,
                    resources.c.status == "queued",
                )
            )
            if updated.rowcount != 1:
                return None
            conn.execute(
                resource_events.insert().values(
                    resource_id=candidate.resource_id,
                    event_type="resource_claimed",
                    actor=worker_id,
                    payload_json={
                        "claim_token_suffix": token[-12:],
                        "lease_expires_at": (
                            lease_expires.isoformat()
                        ),
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id
                    == candidate.resource_id
                )
            ).one()
            record = self._row_to_record(row)
            return record.model_copy(
                update={"claim_token": token}
            )

    def heartbeat(
        self,
        *,
        resource_id: str,
        claim_token: str,
        lease_seconds: float,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        token_hash = _hash_token(claim_token)
        from datetime import timedelta

        lease_expires = now + timedelta(seconds=lease_seconds)
        with self._engine.begin() as conn:
            updated = conn.execute(
                sa.update(resources)
                .values(
                    heartbeat_at=now,
                    lease_expires_at=lease_expires,
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.claim_token_hash == token_hash,
                    resources.c.status == "fetching",
                )
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "heartbeat 失败：claim 已失效或状态非 fetching"
                )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            record = self._row_to_record(row)
            return record.model_copy(
                update={"claim_token": claim_token}
            )

    def mark_validating(
        self,
        *,
        resource_id: str,
        claim_token: str,
    ) -> ResourceRecord:
        return self._fenced_transition(
            resource_id=resource_id,
            claim_token=claim_token,
            from_statuses=["fetching"],
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
        now = database_clock(self._engine)
        token_hash = _hash_token(claim_token)
        with self._engine.begin() as conn:
            updated = conn.execute(
                sa.update(resources)
                .values(
                    status="published",
                    version=resources.c.version + 1,
                    manifest_json=manifest.model_dump(
                        mode="json"
                    ),
                    worker_id=None,
                    claim_token_hash=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    error_json=None,
                    available_at=now,
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.claim_token_hash == token_hash,
                    resources.c.status == "validating",
                )
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "mark_published 失败"
                )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type="resource_published",
                    actor="resource_worker",
                    payload_json={
                        "manifest_sha256": manifest.manifest_sha256,
                        "object_key": manifest.object_key,
                        "size_bytes": manifest.size_bytes,
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row)

    def mark_failed(
        self,
        *,
        resource_id: str,
        claim_token: str,
        error: dict,
        retryable: bool,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        token_hash = _hash_token(claim_token)
        new_status = (
            "failed_retryable" if retryable else "failed_terminal"
        )
        with self._engine.begin() as conn:
            updated = conn.execute(
                sa.update(resources)
                .values(
                    status=new_status,
                    version=resources.c.version + 1,
                    worker_id=None,
                    claim_token_hash=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    error_json=error,
                    available_at=now,
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.claim_token_hash == token_hash,
                    resources.c.status.in_(
                        ["fetching", "validating"]
                    ),
                )
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "mark_failed 失败"
                )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type=f"resource_{new_status}",
                    actor="resource_worker",
                    payload_json={
                        "error_category": error.get("category"),
                        "retryable": retryable,
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row)

    def request_cancel(
        self,
        *,
        resource_id: str,
        reason: str,
        actor: str,
        expected_version: int | None,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        with self._engine.begin() as conn:
            row = conn.execute(
                sa.select(resources)
                .where(resources.c.resource_id == resource_id)
                .with_for_update()
            ).first()
            if row is None:
                raise ResourceNotFoundError(
                    f"resource 不存在：{resource_id}"
                )
            if (
                expected_version is not None
                and row.version != expected_version
            ):
                raise ResourceConflictError(
                    "resource version 冲突"
                )
            if row.status in TERMINAL_RESOURCE_STATUSES:
                raise ResourceConflictError(
                    f"resource 已终态：{row.status}"
                )
            conn.execute(
                sa.update(resources)
                .values(
                    status="cancelled",
                    version=resources.c.version + 1,
                    worker_id=None,
                    claim_token_hash=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    error_json={"reason": reason, "actor": actor},
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id
                )
            )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type="resource_cancelled",
                    actor=actor,
                    payload_json={"reason": reason},
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row)

    def list_expired_fetching(
        self, *, limit: int = 100
    ) -> list[ResourceRecord]:
        now = database_clock(self._engine)
        with self._engine.connect() as conn:
            rows = conn.execute(
                sa.select(resources)
                .where(
                    resources.c.status == "fetching",
                    resources.c.lease_expires_at.is_not(None),
                    resources.c.lease_expires_at < now,
                )
                .order_by(resources.c.lease_expires_at.asc())
                .limit(limit)
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def requeue_expired(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        expired_hash = _hash_token(expired_claim_token)
        with self._engine.begin() as conn:
            updated = conn.execute(
                sa.update(resources)
                .values(
                    status="queued",
                    version=resources.c.version + 1,
                    worker_id=None,
                    claim_token_hash=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    error_json={
                        "category": "lease_expired",
                        "detail": detail,
                    },
                    available_at=now,
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.claim_token_hash == expired_hash,
                    resources.c.status == "fetching",
                )
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "requeue_expired 失败"
                )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type="resource_requeued",
                    actor="reconciler",
                    payload_json={
                        "expired_claim_suffix": (
                            short_secret_hash(expired_claim_token)
                        ),
                        "detail": detail,
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row)

    def require_reconciliation(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        expired_hash = _hash_token(expired_claim_token)
        with self._engine.begin() as conn:
            updated = conn.execute(
                sa.update(resources)
                .values(
                    status="reconciliation_required",
                    version=resources.c.version + 1,
                    error_json={
                        "category": "lease_ambiguous",
                        "detail": detail,
                    },
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.claim_token_hash == expired_hash,
                    resources.c.status == "fetching",
                )
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "require_reconciliation 失败"
                )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type="resource_reconciliation_required",
                    actor="reconciler",
                    payload_json={
                        "expired_claim_suffix": (
                            short_secret_hash(expired_claim_token)
                        ),
                        "detail": detail,
                    },
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            return self._row_to_record(row)

    def list_events(
        self,
        resource_id: str,
        *,
        limit: int = 200,
    ) -> list[ResourceEvent]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                sa.select(resource_events)
                .where(resource_events.c.resource_id == resource_id)
                .order_by(resource_events.c.event_id.desc())
                .limit(limit)
            ).fetchall()
        return [
            ResourceEvent(
                event_id=row.event_id,
                resource_id=row.resource_id,
                event_type=row.event_type,
                actor=row.actor,
                payload=row.payload_json
                if isinstance(row.payload_json, dict)
                else {},
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]

    def _fenced_transition(
        self,
        *,
        resource_id: str,
        claim_token: str,
        from_statuses: list[str],
        to_status: str,
        event_type: str,
    ) -> ResourceRecord:
        now = database_clock(self._engine)
        token_hash = _hash_token(claim_token)
        with self._engine.begin() as conn:
            updated = conn.execute(
                sa.update(resources)
                .values(
                    status=to_status,
                    version=resources.c.version + 1,
                    updated_at=now,
                )
                .where(
                    resources.c.resource_id == resource_id,
                    resources.c.claim_token_hash == token_hash,
                    resources.c.status.in_(from_statuses),
                )
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    f"fenced transition 到 {to_status} 失败"
                )
            conn.execute(
                resource_events.insert().values(
                    resource_id=resource_id,
                    event_type=event_type,
                    actor="resource_worker",
                    payload_json={"to_status": to_status},
                    created_at=now,
                )
            )
            row = conn.execute(
                sa.select(resources).where(
                    resources.c.resource_id == resource_id
                )
            ).one()
            record = self._row_to_record(row)
            return record.model_copy(
                update={"claim_token": claim_token}
            )
