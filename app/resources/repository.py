from __future__ import annotations

"""Phase 29 SQLite ResourceRepository。

所有状态更新都使用 ``WHERE resource_id=? AND claim_token=? AND status IN (...)``
的 fencing 条件。旧 Worker 即使稍后完成下载，也不能发布新 claim 的资源。

claim_token 只保存 SHA-256 哈希（``short_secret_hash`` 只用于日志/event payload
的脱敏 suffix）；原始 token 永不写入 DB。
"""

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.observability.context import short_secret_hash
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


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


def _dump(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _load(value: str | None, default: object) -> object:
    if value is None:
        return default
    return json.loads(value)


def _hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


class SqliteResourceRepository:
    """SQLite 实现的 ResourceRepository。

    单进程开发/离线测试使用；生产 PostgreSQL 由 postgres_repository.py 提供。
    两者共享同一 ResourceRepository 端口语义，但 lease 时钟与持久化边界独立。
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    resource_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_sha256 TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    approval_json TEXT,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    worker_id TEXT,
                    claim_token_hash TEXT,
                    heartbeat_at REAL,
                    lease_expires_at REAL,
                    manifest_json TEXT,
                    error_json TEXT,
                    available_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS ix_resources_claim
                ON resources (status, available_at, created_at);

                CREATE INDEX IF NOT EXISTS ix_resources_lease
                ON resources (status, lease_expires_at);

                CREATE TABLE IF NOT EXISTS resource_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (resource_id)
                        REFERENCES resources(resource_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS
                    ix_resource_events_resource
                ON resource_events (resource_id, event_id);
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def _row_to_record(
        self, row: sqlite3.Row
    ) -> ResourceRecord:
        request = ResourceRequest.model_validate(
            _load(row["request_json"], {})
        )
        approval_raw = _load(
            row["approval_json"], None
        )
        approval = (
            ResourceApproval.model_validate(approval_raw)
            if approval_raw is not None
            else None
        )
        manifest_raw = _load(
            row["manifest_json"], None
        )
        manifest = (
            ResourceManifest.model_validate(manifest_raw)
            if manifest_raw is not None
            else None
        )
        error = _load(row["error_json"], None)
        return ResourceRecord(
            resource_id=row["resource_id"],
            idempotency_key=row["idempotency_key"],
            request=request,
            request_sha256=row["request_sha256"],
            approval=approval,
            status=row["status"],
            version=row["version"],
            attempt_count=row["attempt_count"],
            worker_id=row["worker_id"],
            claim_token=None,
            heartbeat_at=(
                _iso(row["heartbeat_at"])
                if row["heartbeat_at"] is not None
                else None
            ),
            lease_expires_at=(
                _iso(row["lease_expires_at"])
                if row["lease_expires_at"] is not None
                else None
            ),
            manifest=manifest,
            error=error if isinstance(error, dict) else None,
            created_at=_iso(row["created_at"]),
            updated_at=_iso(row["updated_at"]),
        )

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        resource_id: str,
        event_type: str,
        actor: str,
        payload: dict,
    ) -> None:
        connection.execute(
            """
            INSERT INTO resource_events (
                resource_id,
                event_type,
                actor,
                payload_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                resource_id,
                event_type,
                actor,
                _dump(payload),
                time.time(),
            ),
        )

    def submit(
        self,
        *,
        resource_id: str,
        idempotency_key: str,
        request: ResourceRequest,
        request_sha256: str,
    ) -> tuple[ResourceRecord, bool]:
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM resources
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["request_sha256"]
                    != request_sha256
                ):
                    raise ResourceConflictError(
                        "idempotency_key 已绑定不同 request"
                    )
                record = self._row_to_record(existing)
                connection.commit()
                return record, False

            connection.execute(
                """
                INSERT INTO resources (
                    resource_id,
                    idempotency_key,
                    request_sha256,
                    request_json,
                    approval_json,
                    status,
                    version,
                    attempt_count,
                    worker_id,
                    claim_token_hash,
                    heartbeat_at,
                    lease_expires_at,
                    manifest_json,
                    error_json,
                    available_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, NULL, 'awaiting_approval',
                    0, 0, NULL, NULL, NULL, NULL,
                    NULL, NULL, ?, ?, ?
                )
                """,
                (
                    resource_id,
                    idempotency_key,
                    request_sha256,
                    _dump(request.model_dump(mode="json")),
                    now,
                    now,
                    now,
                ),
            )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type="resource_submitted",
                actor="api",
                payload={
                    "kind": request.kind,
                    "request_sha256": request_sha256,
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row), True
        except ResourceConflictError:
            connection.rollback()
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, resource_id: str) -> ResourceRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
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
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            if row is None:
                raise ResourceNotFoundError(
                    f"resource 不存在：{resource_id}"
                )
            if (
                expected_version is not None
                and row["version"] != expected_version
            ):
                raise ResourceConflictError(
                    "resource version 冲突"
                )
            if row["status"] not in {
                "awaiting_approval",
                "rejected",
            }:
                raise ResourceConflictError(
                    f"resource 当前状态 {row['status']} 不可审批"
                )
            if approval.decision == "approved":
                new_status = "queued"
            else:
                new_status = "rejected"
            connection.execute(
                """
                UPDATE resources
                SET approval_json = ?,
                    status = ?,
                    version = version + 1,
                    available_at = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND status IN ('awaiting_approval', 'rejected')
                """,
                (
                    _dump(approval.model_dump(mode="json")),
                    new_status,
                    now if new_status == "queued" else row["available_at"],
                    now,
                    resource_id,
                ),
            )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type=f"resource_{approval.decision}",
                actor=approval.decided_by,
                payload={
                    "decision": approval.decision,
                    "request_sha256": approval.request_sha256,
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
    ) -> ResourceRecord | None:
        now = time.time()
        token = f"rclaim_{uuid4().hex}"
        token_hash = _hash_token(token)
        lease_expires = now + lease_seconds
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            candidate = connection.execute(
                """
                SELECT * FROM resources
                WHERE status = 'queued'
                  AND available_at <= ?
                ORDER BY available_at ASC, created_at ASC
                LIMIT 1
                """,
                (now,),
            ).fetchone()
            if candidate is None:
                connection.commit()
                return None
            updated = connection.execute(
                """
                UPDATE resources
                SET status = 'fetching',
                    version = version + 1,
                    attempt_count = attempt_count + 1,
                    worker_id = ?,
                    claim_token_hash = ?,
                    heartbeat_at = ?,
                    lease_expires_at = ?,
                    error_json = NULL,
                    available_at = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND status = 'queued'
                """,
                (
                    worker_id,
                    token_hash,
                    now,
                    lease_expires,
                    now,
                    now,
                    candidate["resource_id"],
                ),
            )
            if updated.rowcount != 1:
                connection.commit()
                return None
            self._append_event(
                connection,
                resource_id=candidate["resource_id"],
                event_type="resource_claimed",
                actor=worker_id,
                payload={
                    "claim_token_suffix": token[-12:],
                    "lease_expires_at": _iso(lease_expires),
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (candidate["resource_id"],),
            ).fetchone()
            connection.commit()
            assert row is not None
            record = self._row_to_record(row)
            # claim_token 不持久化明文，只在返回给当前 Worker 时附带。
            return record.model_copy(
                update={"claim_token": token}
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def heartbeat(
        self,
        *,
        resource_id: str,
        claim_token: str,
        lease_seconds: float,
    ) -> ResourceRecord:
        now = time.time()
        token_hash = _hash_token(claim_token)
        lease_expires = now + lease_seconds
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE resources
                SET heartbeat_at = ?,
                    lease_expires_at = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND claim_token_hash = ?
                  AND status = 'fetching'
                """,
                (
                    now,
                    lease_expires,
                    now,
                    resource_id,
                    token_hash,
                ),
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "heartbeat 失败：claim 已失效或状态非 fetching"
                )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            record = self._row_to_record(row)
            return record.model_copy(
                update={"claim_token": claim_token}
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_validating(
        self,
        *,
        resource_id: str,
        claim_token: str,
    ) -> ResourceRecord:
        return self._fenced_transition(
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
        now = time.time()
        token_hash = _hash_token(claim_token)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE resources
                SET status = 'published',
                    version = version + 1,
                    manifest_json = ?,
                    worker_id = NULL,
                    claim_token_hash = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    error_json = NULL,
                    available_at = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND claim_token_hash = ?
                  AND status = 'validating'
                """,
                (
                    _dump(manifest.model_dump(mode="json")),
                    now,
                    now,
                    resource_id,
                    token_hash,
                ),
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "mark_published 失败：claim 已失效或状态非 validating"
                )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type="resource_published",
                actor="resource_worker",
                payload={
                    "manifest_sha256": manifest.manifest_sha256,
                    "object_key": manifest.object_key,
                    "size_bytes": manifest.size_bytes,
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_failed(
        self,
        *,
        resource_id: str,
        claim_token: str,
        error: dict,
        retryable: bool,
    ) -> ResourceRecord:
        now = time.time()
        token_hash = _hash_token(claim_token)
        new_status = (
            "failed_retryable" if retryable else "failed_terminal"
        )
        available_at = now if retryable else now
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE resources
                SET status = ?,
                    version = version + 1,
                    worker_id = NULL,
                    claim_token_hash = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = ?,
                    error_json = ?,
                    available_at = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND claim_token_hash = ?
                  AND status IN ('fetching', 'validating')
                """,
                (
                    new_status,
                    None if not retryable else now + 0,
                    _dump(error),
                    available_at,
                    now,
                    resource_id,
                    token_hash,
                ),
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "mark_failed 失败：claim 已失效或状态非 fetching/validating"
                )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type=f"resource_{new_status}",
                actor="resource_worker",
                payload={
                    "error_category": error.get("category"),
                    "retryable": retryable,
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def request_cancel(
        self,
        *,
        resource_id: str,
        reason: str,
        actor: str,
        expected_version: int | None,
    ) -> ResourceRecord:
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            if row is None:
                raise ResourceNotFoundError(
                    f"resource 不存在：{resource_id}"
                )
            if (
                expected_version is not None
                and row["version"] != expected_version
            ):
                raise ResourceConflictError(
                    "resource version 冲突"
                )
            if row["status"] in TERMINAL_RESOURCE_STATUSES:
                raise ResourceConflictError(
                    f"resource 已终态：{row['status']}"
                )
            connection.execute(
                """
                UPDATE resources
                SET status = 'cancelled',
                    version = version + 1,
                    worker_id = NULL,
                    claim_token_hash = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    error_json = ?,
                    updated_at = ?
                WHERE resource_id = ?
                """,
                (
                    _dump({"reason": reason, "actor": actor}),
                    now,
                    resource_id,
                ),
            )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type="resource_cancelled",
                actor=actor,
                payload={"reason": reason},
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_expired_fetching(
        self, *, limit: int = 100
    ) -> list[ResourceRecord]:
        now = time.time()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM resources
                WHERE status = 'fetching'
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at < ?
                ORDER BY lease_expires_at ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def requeue_expired(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        now = time.time()
        expired_hash = _hash_token(expired_claim_token)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE resources
                SET status = 'queued',
                    version = version + 1,
                    worker_id = NULL,
                    claim_token_hash = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    error_json = ?,
                    available_at = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND claim_token_hash = ?
                  AND status = 'fetching'
                """,
                (
                    _dump(
                        {
                            "category": "lease_expired",
                            "detail": detail,
                        }
                    ),
                    now,
                    now,
                    resource_id,
                    expired_hash,
                ),
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "requeue_expired 失败：claim 不匹配或状态非 fetching"
                )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type="resource_requeued",
                actor="reconciler",
                payload={
                    "expired_claim_suffix": (
                        short_secret_hash(expired_claim_token)
                    ),
                    "detail": detail,
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def require_reconciliation(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        now = time.time()
        expired_hash = _hash_token(expired_claim_token)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE resources
                SET status = 'reconciliation_required',
                    version = version + 1,
                    error_json = ?,
                    updated_at = ?
                WHERE resource_id = ?
                  AND claim_token_hash = ?
                  AND status = 'fetching'
                """,
                (
                    _dump(
                        {
                            "category": "lease_ambiguous",
                            "detail": detail,
                        }
                    ),
                    now,
                    resource_id,
                    expired_hash,
                ),
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    "require_reconciliation 失败：claim 不匹配或状态非 fetching"
                )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type="resource_reconciliation_required",
                actor="reconciler",
                payload={
                    "expired_claim_suffix": (
                        short_secret_hash(expired_claim_token)
                    ),
                    "detail": detail,
                },
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_events(
        self,
        resource_id: str,
        *,
        limit: int = 200,
    ) -> list[ResourceEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM resource_events
                WHERE resource_id = ?
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (resource_id, limit),
            ).fetchall()
        return [
            ResourceEvent(
                event_id=row["event_id"],
                resource_id=row["resource_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=_load(row["payload_json"], {}),
                created_at=_iso(row["created_at"]),
            )
            for row in rows
        ]

    def _fenced_transition(
        self,
        *,
        resource_id: str,
        claim_token: str,
        from_statuses: set[str],
        to_status: str,
        event_type: str,
    ) -> ResourceRecord:
        now = time.time()
        token_hash = _hash_token(claim_token)
        placeholders = ",".join(
            "?" for _ in from_statuses
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                f"""
                UPDATE resources
                SET status = ?,
                    version = version + 1,
                    updated_at = ?
                WHERE resource_id = ?
                  AND claim_token_hash = ?
                  AND status IN ({placeholders})
                """,
                (
                    to_status,
                    now,
                    resource_id,
                    token_hash,
                    *from_statuses,
                ),
            )
            if updated.rowcount != 1:
                raise ResourceStateAmbiguous(
                    f"fenced transition 到 {to_status} 失败"
                )
            self._append_event(
                connection,
                resource_id=resource_id,
                event_type=event_type,
                actor="resource_worker",
                payload={"to_status": to_status},
            )
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            record = self._row_to_record(row)
            return record.model_copy(
                update={"claim_token": claim_token}
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Phase 35: Retention methods
    # ------------------------------------------------------------------

    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int:
        if backend not in {"local", "s3"}:
            return 0
        count = 0
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT manifest_json
                FROM resources
                WHERE manifest_json IS NOT NULL
                """
            ).fetchall()
        from app.resources.schemas import ResourceManifest
        for row in rows:
            manifest = ResourceManifest.model_validate_json(row["manifest_json"])
            if manifest.object_key == object_key:
                count += 1
        return count


def build_resource_repository():
    """Composition root：根据 settings 选择 SQLite/PostgreSQL backend。"""

    from app.config import settings

    if settings.job_store_backend == "sqlite":
        repo = SqliteResourceRepository(
            settings.resource_db_path
        )
    elif settings.job_store_backend == "postgresql":
        from app.resources.postgres_repository import (
            PostgresResourceRepository,
        )

        repo = PostgresResourceRepository()
    else:
        raise ValueError(
            "不支持的 resource backend"
        )
    repo.initialize()
    return repo
