from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from app.research_browser.errors import (
    ResearchConflict,
    ResearchIntegrityError,
    ResearchNotFound,
)
from app.research_browser.identity import sha256_value, without_hash
from app.research_browser.schemas import (
    ResearchEvent,
    ResearchEvidencePack,
    ResearchRecord,
    ResearchRequest,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat()


class SqliteResearchRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_sessions (
                    session_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_sha256 TEXT NOT NULL,
                    policy_sha256 TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    job_id TEXT,
                    project_id TEXT,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    lease_token TEXT,
                    lease_expires_at TEXT,
                    pack_id TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_research_job
                    ON research_sessions(job_id, status, updated_at);

                CREATE TABLE IF NOT EXISTS research_packs (
                    pack_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL UNIQUE,
                    pack_sha256 TEXT NOT NULL,
                    pack_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES research_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS research_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES research_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS research_resource_links (
                    session_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    candidate_sha256 TEXT NOT NULL,
                    pack_sha256 TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    resource_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(session_id, candidate_id),
                    FOREIGN KEY(session_id) REFERENCES research_sessions(session_id)
                );
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    @staticmethod
    def _record(row: sqlite3.Row) -> ResearchRecord:
        return ResearchRecord(
            session_id=row["session_id"],
            idempotency_key=row["idempotency_key"],
            request=ResearchRequest.model_validate_json(row["request_json"]),
            request_sha256=row["request_sha256"],
            policy_sha256=row["policy_sha256"],
            status=row["status"],
            version=row["version"],
            attempt_count=row["attempt_count"],
            lease_token=row["lease_token"],
            lease_expires_at=row["lease_expires_at"],
            pack_id=row["pack_id"],
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _event(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: str,
        event_type: str,
        actor: str,
        payload: dict | None = None,
        created_at: str,
    ) -> None:
        # payload 只能放稳定 ID/计数/状态，不放 query、URL 或网页正文。
        connection.execute(
            """
            INSERT INTO research_events(
                session_id, event_type, actor, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                event_type,
                actor,
                json.dumps(payload or {}, sort_keys=True, separators=(",", ":")),
                created_at,
            ),
        )

    def submit(
        self,
        *,
        session_id: str,
        idempotency_key: str,
        request: ResearchRequest,
        request_sha256: str,
        policy_sha256: str,
        actor: str,
    ) -> tuple[ResearchRecord, bool]:
        now = iso(utc_now())
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM research_sessions WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                record = self._record(existing)
                if (
                    record.request_sha256 != request_sha256
                    or record.policy_sha256 != policy_sha256
                ):
                    raise ResearchConflict("RESEARCH_IDEMPOTENCY_CONFLICT")
                return record, False
            connection.execute(
                """
                INSERT INTO research_sessions(
                    session_id, idempotency_key, request_sha256, policy_sha256,
                    request_json, job_id, project_id, status, version,
                    attempt_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', 0, 0, ?, ?)
                """,
                (
                    session_id,
                    idempotency_key,
                    request_sha256,
                    policy_sha256,
                    request.model_dump_json(),
                    request.job_id,
                    request.project_id,
                    now,
                    now,
                ),
            )
            self._event(
                connection,
                session_id=session_id,
                event_type="research.submitted",
                actor=actor,
                payload={"request_sha256": request_sha256},
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            return self._record(row), True

    def get(self, session_id: str) -> ResearchRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise ResearchNotFound("RESEARCH_SESSION_NOT_FOUND")
        return self._record(row)

    def start(
        self,
        *,
        session_id: str,
        expected_version: int,
        lease_token: str,
        lease_seconds: int,
        actor: str,
    ) -> ResearchRecord:
        now_value = utc_now()
        now = iso(now_value)
        expires = iso(now_value + timedelta(seconds=lease_seconds))
        with self._write() as connection:
            cursor = connection.execute(
                """
                UPDATE research_sessions
                SET status='running', version=version+1,
                    attempt_count=attempt_count+1,
                    lease_token=?, lease_expires_at=?, error_code=NULL,
                    updated_at=?
                WHERE session_id=? AND version=?
                  AND status IN ('submitted', 'failed_retryable')
                """,
                (lease_token, expires, now, session_id, expected_version),
            )
            if cursor.rowcount != 1:
                raise ResearchConflict("RESEARCH_START_STALE")
            self._event(
                connection,
                session_id=session_id,
                event_type="research.started",
                actor=actor,
                payload={"attempt_incremented": True},
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            return self._record(row)

    def complete(
        self,
        *,
        session_id: str,
        lease_token: str,
        pack: ResearchEvidencePack,
        actor: str,
    ) -> ResearchRecord:
        expected_pack_hash = sha256_value(without_hash(pack, "pack_sha256"))
        if expected_pack_hash != pack.pack_sha256:
            raise ResearchIntegrityError("RESEARCH_PACK_HASH_INVALID")
        if pack.session_id != session_id:
            raise ResearchIntegrityError("RESEARCH_PACK_SESSION_MISMATCH")
        now = iso(utc_now())
        with self._write() as connection:
            session = connection.execute(
                """
                SELECT request_sha256, policy_sha256
                FROM research_sessions
                WHERE session_id=? AND status='running' AND lease_token=?
                """,
                (session_id, lease_token),
            ).fetchone()
            if session is None:
                raise ResearchConflict("RESEARCH_COMPLETE_LEASE_LOST")
            if pack.request_sha256 != session["request_sha256"]:
                raise ResearchIntegrityError("RESEARCH_PACK_REQUEST_MISMATCH")
            if pack.policy_sha256 != session["policy_sha256"]:
                raise ResearchIntegrityError("RESEARCH_PACK_POLICY_MISMATCH")
            connection.execute(
                """
                INSERT INTO research_packs(
                    pack_id, session_id, pack_sha256, pack_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pack.pack_id,
                    session_id,
                    pack.pack_sha256,
                    pack.model_dump_json(),
                    pack.created_at,
                ),
            )
            cursor = connection.execute(
                """
                UPDATE research_sessions
                SET status='succeeded', version=version+1,
                    lease_token=NULL, lease_expires_at=NULL,
                    pack_id=?, error_code=NULL, updated_at=?
                WHERE session_id=? AND status='running' AND lease_token=?
                """,
                (pack.pack_id, now, session_id, lease_token),
            )
            if cursor.rowcount != 1:
                raise ResearchConflict("RESEARCH_COMPLETE_LEASE_LOST")
            self._event(
                connection,
                session_id=session_id,
                event_type="research.succeeded",
                actor=actor,
                payload={"pack_id": pack.pack_id, "pack_sha256": pack.pack_sha256},
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            return self._record(row)

    def fail(
        self,
        *,
        session_id: str,
        lease_token: str,
        error_code: str,
        retryable: bool,
        actor: str,
    ) -> ResearchRecord:
        status = "failed_retryable" if retryable else "failed_terminal"
        now = iso(utc_now())
        with self._write() as connection:
            cursor = connection.execute(
                """
                UPDATE research_sessions
                SET status=?, version=version+1, lease_token=NULL,
                    lease_expires_at=NULL, error_code=?, updated_at=?
                WHERE session_id=? AND status='running' AND lease_token=?
                """,
                (status, error_code[:100], now, session_id, lease_token),
            )
            if cursor.rowcount != 1:
                raise ResearchConflict("RESEARCH_FAIL_LEASE_LOST")
            self._event(
                connection,
                session_id=session_id,
                event_type="research.failed",
                actor=actor,
                payload={"error_code": error_code[:100], "retryable": retryable},
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            return self._record(row)

    def cancel(
        self,
        *,
        session_id: str,
        expected_version: int,
        actor: str,
    ) -> ResearchRecord:
        now = iso(utc_now())
        with self._write() as connection:
            cursor = connection.execute(
                """
                UPDATE research_sessions
                SET status='cancelled', version=version+1, updated_at=?
                WHERE session_id=? AND version=?
                  AND status IN ('submitted', 'failed_retryable')
                """,
                (now, session_id, expected_version),
            )
            if cursor.rowcount != 1:
                raise ResearchConflict("RESEARCH_CANCEL_STALE_OR_RUNNING")
            self._event(
                connection,
                session_id=session_id,
                event_type="research.cancelled",
                actor=actor,
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            return self._record(row)

    def get_pack(self, session_id: str) -> ResearchEvidencePack:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT pack_json FROM research_packs WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise ResearchNotFound("RESEARCH_PACK_NOT_FOUND")
        pack = ResearchEvidencePack.model_validate_json(row["pack_json"])
        if sha256_value(without_hash(pack, "pack_sha256")) != pack.pack_sha256:
            raise ResearchIntegrityError("RESEARCH_PACK_HASH_INVALID")
        return pack

    def list_packs_for_job(
        self,
        *,
        job_id: str,
        limit: int = 20,
    ) -> list[ResearchEvidencePack]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT p.pack_json
                FROM research_sessions AS s
                JOIN research_packs AS p ON p.session_id=s.session_id
                WHERE s.job_id=? AND s.status='succeeded'
                ORDER BY s.updated_at DESC LIMIT ?
                """,
                (job_id, min(max(limit, 1), 100)),
            ).fetchall()
        packs: list[ResearchEvidencePack] = []
        for row in rows:
            pack = ResearchEvidencePack.model_validate_json(row["pack_json"])
            if sha256_value(without_hash(pack, "pack_sha256")) != pack.pack_sha256:
                raise ResearchIntegrityError("RESEARCH_PACK_HASH_INVALID")
            packs.append(pack)
        return packs

    def list_events(
        self,
        session_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[ResearchEvent]:
        self.get(session_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM research_events
                WHERE session_id=? AND event_id>?
                ORDER BY event_id ASC LIMIT ?
                """,
                (
                    session_id,
                    max(after_event_id, 0),
                    min(max(limit, 1), 500),
                ),
            ).fetchall()
        return [
            ResearchEvent(
                event_id=row["event_id"],
                session_id=row["session_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def requeue_expired(self, *, now: datetime, actor: str) -> int:
        now_text = iso(now)
        with self._write() as connection:
            rows = connection.execute(
                """
                SELECT session_id FROM research_sessions
                WHERE status='running' AND lease_expires_at < ?
                """,
                (now_text,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE research_sessions
                    SET status='failed_retryable', version=version+1,
                        lease_token=NULL, lease_expires_at=NULL,
                        error_code='RESEARCH_LEASE_EXPIRED', updated_at=?
                    WHERE session_id=? AND status='running'
                    """,
                    (now_text, row["session_id"]),
                )
                self._event(
                    connection,
                    session_id=row["session_id"],
                    event_type="research.recovered",
                    actor=actor,
                    payload={"reason": "lease_expired"},
                    created_at=now_text,
                )
            return len(rows)

    def record_resource_link(
        self,
        *,
        session_id: str,
        candidate_id: str,
        candidate_sha256: str,
        pack_sha256: str,
        idempotency_key: str,
        resource_id: str,
    ) -> str:
        now = iso(utc_now())
        with self._write() as connection:
            existing = connection.execute(
                """
                SELECT * FROM research_resource_links
                WHERE idempotency_key=? OR (session_id=? AND candidate_id=?)
                """,
                (idempotency_key, session_id, candidate_id),
            ).fetchone()
            if existing is not None:
                if (
                    existing["candidate_sha256"] != candidate_sha256
                    or existing["pack_sha256"] != pack_sha256
                ):
                    raise ResearchConflict("RESEARCH_RESOURCE_LINK_CONFLICT")
                return str(existing["resource_id"])
            connection.execute(
                """
                INSERT INTO research_resource_links(
                    session_id, candidate_id, candidate_sha256, pack_sha256,
                    idempotency_key, resource_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    candidate_id,
                    candidate_sha256,
                    pack_sha256,
                    idempotency_key,
                    resource_id,
                    now,
                ),
            )
            return resource_id
