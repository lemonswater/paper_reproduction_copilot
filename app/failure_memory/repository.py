from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.failure_memory.errors import (
    FailureCaseConflictError,
    FailureCaseIntegrityError,
    FailureCaseNotFoundError,
)
from app.failure_memory.identity import validate_case_hash
from app.failure_memory.schemas import FailureCaseRecord


class SqliteFailureCaseRepository:
    """单机 Failure Memory；每个方法使用短事务和独立连接。"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS failure_cases (
                    case_id TEXT PRIMARY KEY,
                    source_job_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK (
                        status IN (
                            'candidate',
                            'human_confirmed',
                            'run_verified',
                            'deprecated'
                        )
                    ),
                    version INTEGER NOT NULL CHECK (version >= 0),
                    case_hash TEXT NOT NULL,
                    signature_sha256 TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    code TEXT NOT NULL,
                    exception_type TEXT,
                    error_type TEXT NOT NULL,
                    profile_fingerprint TEXT NOT NULL,
                    repository_commit TEXT,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_failure_cases_lookup
                ON failure_cases (
                    status,
                    stage,
                    code,
                    updated_at DESC
                );

                CREATE INDEX IF NOT EXISTS idx_failure_cases_signature
                ON failure_cases (signature_sha256, status);

                CREATE TABLE IF NOT EXISTS failure_case_operations (
                    operation_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    result_version INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES failure_cases(case_id)
                );
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    @staticmethod
    def _record(row: sqlite3.Row) -> FailureCaseRecord:
        try:
            raw = json.loads(row["record_json"])
            record = FailureCaseRecord.model_validate(raw)
            validate_case_hash(record)
        except Exception as exc:
            raise FailureCaseIntegrityError(
                "Failure Case 持久化内容无效"
            ) from exc

        columns_match = (
            record.case_id == row["case_id"]
            and record.source.job_id == row["source_job_id"]
            and record.status == row["status"]
            and record.version == row["version"]
            and record.case_hash == row["case_hash"]
            and record.signature.signature_sha256
            == row["signature_sha256"]
        )
        if not columns_match:
            raise FailureCaseIntegrityError(
                "Failure Case 检索列与 record_json 身份不一致"
            )
        return record

    @staticmethod
    def _values(record: FailureCaseRecord) -> tuple[object, ...]:
        return (
            record.case_id,
            record.source.job_id,
            record.status,
            record.version,
            record.case_hash,
            record.signature.signature_sha256,
            record.signature.stage,
            record.signature.code,
            record.signature.exception_type,
            record.signature.error_type,
            record.source.environment.execution_profile_fingerprint,
            record.source.environment.repository_commit,
            json.dumps(
                record.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            record.created_at,
            record.updated_at,
        )

    def get(self, case_id: str) -> FailureCaseRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM failure_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            raise FailureCaseNotFoundError(
                f"Failure Case 不存在：{case_id}"
            )
        return self._record(row)

    def find_by_source_job(
        self,
        source_job_id: str,
    ) -> FailureCaseRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM failure_cases
                WHERE source_job_id = ?
                """,
                (source_job_id,),
            ).fetchone()
        return None if row is None else self._record(row)

    def find_replay(
        self,
        *,
        operation_key: str,
        request_hash: str,
    ) -> FailureCaseRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT request_hash, result_json
                FROM failure_case_operations
                WHERE operation_key = ?
                """,
                (operation_key,),
            ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise FailureCaseConflictError(
                "Idempotency-Key 已被不同 Failure Memory 请求使用"
            )
        try:
            replay = FailureCaseRecord.model_validate_json(
                row["result_json"]
            )
            validate_case_hash(replay)
            return replay
        except Exception as exc:
            raise FailureCaseIntegrityError(
                "Failure Memory 幂等响应已损坏"
            ) from exc

    def create(
        self,
        *,
        record: FailureCaseRecord,
        operation_key: str,
        request_hash: str,
    ) -> FailureCaseRecord:
        validate_case_hash(record)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                """
                SELECT request_hash, result_json
                FROM failure_case_operations
                WHERE operation_key = ?
                """,
                (operation_key,),
            ).fetchone()
            if replay is not None:
                if replay["request_hash"] != request_hash:
                    raise FailureCaseConflictError(
                        "Idempotency-Key 请求内容冲突"
                    )
                connection.commit()
                result = FailureCaseRecord.model_validate_json(
                    replay["result_json"]
                )
                validate_case_hash(result)
                return result

            connection.execute(
                """
                INSERT INTO failure_cases (
                    case_id, source_job_id, status, version, case_hash,
                    signature_sha256, stage, code, exception_type,
                    error_type, profile_fingerprint, repository_commit,
                    record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._values(record),
            )
            connection.execute(
                """
                INSERT INTO failure_case_operations (
                    operation_key, request_hash, case_id,
                    result_version, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_key,
                    request_hash,
                    record.case_id,
                    record.version,
                    record.model_dump_json(),
                    record.updated_at,
                ),
            )
            connection.commit()
            return record
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise FailureCaseConflictError(
                "同一源 Job 已经存在 Failure Case"
            ) from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def replace(
        self,
        *,
        record: FailureCaseRecord,
        expected_version: int,
        expected_case_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> FailureCaseRecord:
        validate_case_hash(record)
        if record.version != expected_version + 1:
            raise ValueError("replace 必须使 version 恰好增加 1")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                """
                SELECT request_hash, result_json
                FROM failure_case_operations
                WHERE operation_key = ?
                """,
                (operation_key,),
            ).fetchone()
            if replay is not None:
                if replay["request_hash"] != request_hash:
                    raise FailureCaseConflictError(
                        "Idempotency-Key 请求内容冲突"
                    )
                connection.commit()
                result = FailureCaseRecord.model_validate_json(
                    replay["result_json"]
                )
                validate_case_hash(result)
                return result

            current = connection.execute(
                """
                SELECT version, case_hash, status
                FROM failure_cases
                WHERE case_id = ?
                """,
                (record.case_id,),
            ).fetchone()
            if current is None:
                raise FailureCaseNotFoundError(
                    f"Failure Case 不存在：{record.case_id}"
                )
            if (
                current["version"] != expected_version
                or current["case_hash"] != expected_case_hash
            ):
                raise FailureCaseConflictError(
                    "Failure Case version 或 hash 已变化，请刷新后重试"
                )

            cursor = connection.execute(
                """
                UPDATE failure_cases
                SET status = ?, version = ?, case_hash = ?,
                    signature_sha256 = ?, stage = ?, code = ?,
                    exception_type = ?, error_type = ?,
                    profile_fingerprint = ?, repository_commit = ?,
                    record_json = ?, updated_at = ?
                WHERE case_id = ?
                  AND version = ?
                  AND case_hash = ?
                """,
                (
                    record.status,
                    record.version,
                    record.case_hash,
                    record.signature.signature_sha256,
                    record.signature.stage,
                    record.signature.code,
                    record.signature.exception_type,
                    record.signature.error_type,
                    record.source.environment.execution_profile_fingerprint,
                    record.source.environment.repository_commit,
                    json.dumps(
                        record.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    record.updated_at,
                    record.case_id,
                    expected_version,
                    expected_case_hash,
                ),
            )
            if cursor.rowcount != 1:
                raise FailureCaseConflictError(
                    "Failure Case CAS 更新失败"
                )
            connection.execute(
                """
                INSERT INTO failure_case_operations (
                    operation_key, request_hash, case_id,
                    result_version, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_key,
                    request_hash,
                    record.case_id,
                    record.version,
                    record.model_dump_json(),
                    record.updated_at,
                ),
            )
            connection.commit()
            return record
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_candidates(
        self,
        *,
        stage: str,
        code: str,
        limit: int,
    ) -> list[FailureCaseRecord]:
        """先按强结构信号缩小集合，再由 Retriever 精排。"""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM failure_cases
                WHERE status != 'deprecated'
                  AND (stage = ? OR code = ?)
                ORDER BY
                    CASE status
                        WHEN 'run_verified' THEN 0
                        WHEN 'human_confirmed' THEN 1
                        ELSE 2
                    END,
                    updated_at DESC,
                    case_id ASC
                LIMIT ?
                """,
                (stage, code, max(1, min(limit, 500))),
            ).fetchall()
        return [self._record(row) for row in rows]

    def list_records(
        self,
        *,
        include_deprecated: bool,
        limit: int,
    ) -> list[FailureCaseRecord]:
        where = "" if include_deprecated else "WHERE status != 'deprecated'"
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM failure_cases
                {where}
                ORDER BY updated_at DESC, case_id ASC
                LIMIT ?
                """,
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [self._record(row) for row in rows]

    def active_referenced_job_ids(self) -> set[str]:
        """活跃 Case 的源 Run 和验证 Run 都形成 Retention 引用边。"""

        # Retention 安全查询不能使用 UI page limit，否则第 501 条引用会漏掉。
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM failure_cases
                WHERE status != 'deprecated'
                ORDER BY case_id ASC
                """
            ).fetchall()
        records = [self._record(row) for row in rows]
        job_ids = {item.source.job_id for item in records}
        job_ids.update(
            item.verification.job_id
            for item in records
            if item.verification is not None
        )
        return job_ids
