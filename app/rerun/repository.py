# app/rerun/repository.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.rerun.errors import (
    RerunConflictError,
    RerunExpiredError,
    RerunIntegrityError,
    RerunNotFoundError,
)
from app.rerun.identity import validate_proposal_hash
from app.rerun.schemas import (
    RerunProposal,
    RerunProposalRecord,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_expired(proposal: RerunProposal, now: str) -> bool:
    return proposal.expires_at <= now


class SqliteRerunRepository:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.path = path
        self.clock = clock

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=30.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rerun_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    proposal_hash TEXT NOT NULL UNIQUE,
                    create_idempotency_key TEXT NOT NULL UNIQUE,
                    create_request_hash TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    child_job_id TEXT,
                    submit_idempotency_key TEXT,
                    last_error TEXT,
                    cancel_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rerun_parent_job
                ON rerun_proposals(
                    json_extract(proposal_json, '$.source.parent_job_id'),
                    created_at DESC
                )
                """
            )
        finally:
            connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> RerunProposalRecord:
        proposal = RerunProposal.model_validate_json(row["proposal_json"])
        validate_proposal_hash(proposal)
        if proposal.proposal_id != row["proposal_id"]:
            raise RerunIntegrityError("Proposal row identity 不一致")
        if proposal.proposal_hash != row["proposal_hash"]:
            raise RerunIntegrityError("Proposal row hash 不一致")
        return RerunProposalRecord(
            proposal=proposal,
            status=row["status"],
            version=row["version"],
            child_job_id=row["child_job_id"],
            submit_idempotency_key=row["submit_idempotency_key"],
            last_error=row["last_error"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_by_id(
        connection: sqlite3.Connection,
        proposal_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM rerun_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            raise RerunNotFoundError(
                f"Rerun Proposal 不存在：{proposal_id}"
            )
        return row

    def _expire_if_needed(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> sqlite3.Row:
        record = self._record(row)
        if (
            record.status == "pending"
            and _is_expired(record.proposal, self.clock())
        ):
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'expired', version = version + 1, updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (self.clock(), record.proposal.proposal_id, record.version),
            )
            return self._row_by_id(
                connection,
                record.proposal.proposal_id,
            )
        return row

    def create(
        self,
        *,
        proposal: RerunProposal,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[RerunProposalRecord, bool]:
        validate_proposal_hash(proposal)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM rerun_proposals
                WHERE create_idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["create_request_hash"] != request_hash:
                    raise RerunConflictError(
                        "创建 Proposal 的幂等键已绑定其他请求"
                    )
                connection.execute("COMMIT")
                return self._record(existing), False

            now = self.clock()
            connection.execute(
                """
                INSERT INTO rerun_proposals (
                    proposal_id, proposal_hash,
                    create_idempotency_key, create_request_hash,
                    proposal_json, status, version,
                    child_job_id, submit_idempotency_key,
                    last_error, cancel_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', 0, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.proposal_hash,
                    idempotency_key,
                    request_hash,
                    proposal.model_dump_json(),
                    now,
                    now,
                ),
            )
            row = self._row_by_id(connection, proposal.proposal_id)
            connection.execute("COMMIT")
            return self._record(row), True
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def get(self, proposal_id: str) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._row_by_id(connection, proposal_id)
            row = self._expire_if_needed(connection, row)
            connection.execute("COMMIT")
            return self._record(row)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def find_create_replay(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
    ) -> RerunProposalRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT * FROM rerun_proposals
                WHERE create_idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if row is None:
                return None
            if row["create_request_hash"] != request_hash:
                raise RerunConflictError(
                    "创建 Proposal 的幂等键已绑定其他请求"
                )
            proposal_id = str(row["proposal_id"])
        finally:
            connection.close()
        # 复用 get() 的 pending -> expired 原子投影。
        return self.get(proposal_id)

    def begin_submission(
        self,
        *,
        proposal_id: str,
        expected_hash: str,
        expected_version: int,
        submit_idempotency_key: str,
    ) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._expire_if_needed(
                connection,
                self._row_by_id(connection, proposal_id),
            )
            record = self._record(row)
            if record.proposal.proposal_hash != expected_hash:
                raise RerunConflictError("Proposal hash 已变化")
            if record.status == "expired":
                raise RerunExpiredError("Proposal 已过期")
            if record.status == "submitted":
                connection.execute("COMMIT")
                return record
            if record.status == "submitting":
                if record.submit_idempotency_key != submit_idempotency_key:
                    raise RerunConflictError("Proposal 正由其他提交操作处理")
                connection.execute("COMMIT")
                return record
            if record.status != "pending":
                raise RerunConflictError(
                    f"Proposal 当前不能提交：{record.status}"
                )
            if record.version != expected_version:
                raise RerunConflictError(
                    "Proposal version 已变化，请刷新后重试"
                )

            now = self.clock()
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'submitting',
                    submit_idempotency_key = ?,
                    last_error = NULL,
                    version = version + 1,
                    updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (
                    submit_idempotency_key,
                    now,
                    proposal_id,
                    record.version,
                ),
            )
            updated = self._record(
                self._row_by_id(connection, proposal_id)
            )
            connection.execute("COMMIT")
            return updated
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def complete_submission(
        self,
        *,
        proposal_id: str,
        submit_idempotency_key: str,
        child_job_id: str,
    ) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            record = self._record(
                self._row_by_id(connection, proposal_id)
            )
            if record.status == "submitted":
                if record.child_job_id != child_job_id:
                    raise RerunIntegrityError(
                        "Proposal 已绑定另一个 child Job"
                    )
                connection.execute("COMMIT")
                return record
            if (
                record.status != "submitting"
                or record.submit_idempotency_key != submit_idempotency_key
            ):
                raise RerunConflictError("Proposal submission ownership 不匹配")

            now = self.clock()
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'submitted',
                    child_job_id = ?,
                    version = version + 1,
                    updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (child_job_id, now, proposal_id, record.version),
            )
            updated = self._record(
                self._row_by_id(connection, proposal_id)
            )
            connection.execute("COMMIT")
            return updated
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def record_submission_error(
        self,
        *,
        proposal_id: str,
        submit_idempotency_key: str,
        detail: str,
    ) -> None:
        """保持 submitting，重试仍使用同一 Job 幂等键消歧。"""

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            record = self._record(
                self._row_by_id(connection, proposal_id)
            )
            if (
                record.status == "submitting"
                and record.submit_idempotency_key == submit_idempotency_key
            ):
                connection.execute(
                    """
                    UPDATE rerun_proposals
                    SET last_error = ?, version = version + 1, updated_at = ?
                    WHERE proposal_id = ? AND version = ?
                    """,
                    (detail[:1000], self.clock(), proposal_id, record.version),
                )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def cancel(
        self,
        *,
        proposal_id: str,
        expected_hash: str,
        expected_version: int,
        reason: str,
    ) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._expire_if_needed(
                connection,
                self._row_by_id(connection, proposal_id),
            )
            record = self._record(row)
            if record.proposal.proposal_hash != expected_hash:
                raise RerunConflictError("Proposal hash 已变化")
            if record.status == "cancelled":
                connection.execute("COMMIT")
                return record
            if record.status != "pending":
                raise RerunConflictError(
                    f"只有 pending Proposal 可以取消：{record.status}"
                )
            if record.version != expected_version:
                raise RerunConflictError("Proposal version 已变化")
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'cancelled', cancel_reason = ?,
                    version = version + 1, updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (reason, self.clock(), proposal_id, record.version),
            )
            updated = self._record(
                self._row_by_id(connection, proposal_id)
            )
            connection.execute("COMMIT")
            return updated
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def ping(self) -> bool:
        connection = self._connect()
        try:
            return connection.execute("SELECT 1").fetchone()[0] == 1
        finally:
            connection.close()
