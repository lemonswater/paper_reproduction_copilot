from __future__ import annotations

import sqlite3
from pathlib import Path

from app.mcp_export.schemas import McpExportAuditRecord


class SqliteMcpExportAuditRepository:
    """只保存调用身份和 Hash，不保存 Token、query 或 Tool 输出。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_export_calls (
                    call_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    actor_fingerprint TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    output_sha256 TEXT,
                    error_code TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mcp_export_calls_job
                ON mcp_export_calls(job_id, started_at, call_id)
                """
            )

    def put(self, record: McpExportAuditRecord) -> None:
        payload = record.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mcp_export_calls (
                    call_id, request_id, actor_fingerprint,
                    operation, job_id, status, input_sha256,
                    output_sha256, error_code, started_at,
                    finished_at, duration_ms, record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.call_id,
                    record.request_id,
                    record.actor_fingerprint,
                    record.operation,
                    record.job_id,
                    record.status,
                    record.input_sha256,
                    record.output_sha256,
                    record.error_code,
                    record.started_at,
                    record.finished_at,
                    record.duration_ms,
                    payload,
                ),
            )

    def list_for_job(
        self,
        job_id: str,
        *,
        limit: int = 100,
    ) -> list[McpExportAuditRecord]:
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT record_json
                FROM mcp_export_calls
                WHERE job_id = ?
                ORDER BY started_at DESC, call_id DESC
                LIMIT ?
                """,
                (job_id, bounded),
            ).fetchall()
        return [
            McpExportAuditRecord.model_validate_json(row["record_json"])
            for row in rows
        ]

    def delete_for_job(self, job_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM mcp_export_calls WHERE job_id = ?",
                (job_id,),
            )
        return max(cursor.rowcount, 0)

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()
