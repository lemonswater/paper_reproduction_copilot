from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.mcp_gateway.errors import McpEvidenceIntegrityError
from app.mcp_gateway.identity import validate_pack_hash
from app.mcp_gateway.schemas import (
    McpCallRecord,
    McpEvidencePack,
)


class SqliteMcpEvidenceRepository:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS mcp_evidence_packs (
                    pack_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    server_id TEXT NOT NULL,
                    binding_id TEXT NOT NULL,
                    pack_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mcp_pack_job_created
                ON mcp_evidence_packs(job_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS mcp_call_records (
                    call_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    server_id TEXT NOT NULL,
                    binding_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    request_sha256 TEXT NOT NULL,
                    result_sha256 TEXT,
                    started_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mcp_call_job_started
                ON mcp_call_records(job_id, started_at DESC);
                """
            )

    def _decode_pack(self, raw: str) -> McpEvidencePack:
        try:
            pack = McpEvidencePack.model_validate_json(raw)
            validate_pack_hash(pack)
            return pack
        except Exception as exc:
            raise McpEvidenceIntegrityError(
                "stored MCP Evidence Pack is invalid"
            ) from exc

    def put_success(
        self,
        *,
        pack: McpEvidencePack,
        record: McpCallRecord,
    ) -> None:
        validate_pack_hash(pack)
        if record.status != "succeeded":
            raise ValueError("put_success requires succeeded record")
        if record.job_id != pack.job_id:
            raise ValueError("MCP record and pack job_id mismatch")
        if record.server_id != pack.server_id:
            raise ValueError("MCP record and pack server_id mismatch")
        if record.binding_id != pack.binding_id:
            raise ValueError("MCP record and pack binding_id mismatch")
        if record.result_sha256 != pack.result_sha256:
            raise ValueError("MCP record and pack result hash mismatch")
        pack_json = pack.model_dump_json()
        record_json = record.model_dump_json()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT payload_json FROM mcp_evidence_packs WHERE pack_id = ?",
                (pack.pack_id,),
            ).fetchone()
            if existing is not None and existing["payload_json"] != pack_json:
                raise McpEvidenceIntegrityError(
                    "MCP pack_id already exists with different payload"
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO mcp_evidence_packs(
                    pack_id, job_id, server_id, binding_id,
                    pack_sha256, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (pack.pack_id, pack.job_id, pack.server_id, pack.binding_id, pack.pack_sha256, pack.created_at, pack_json),
            )
            connection.execute(
                """
                INSERT INTO mcp_call_records(
                    call_id, job_id, server_id, binding_id,
                    status, error_code, request_sha256,
                    result_sha256, started_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (record.call_id, record.job_id, record.server_id, record.binding_id, record.status, record.error_code, record.request_sha256, record.result_sha256, record.started_at, record_json),
            )

    def put_failure(self, record: McpCallRecord) -> None:
        if record.status != "failed":
            raise ValueError("put_failure requires failed record")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mcp_call_records(
                    call_id, job_id, server_id, binding_id,
                    status, error_code, request_sha256,
                    result_sha256, started_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (record.call_id, record.job_id, record.server_id, record.binding_id, record.status, record.error_code, record.request_sha256, record.result_sha256, record.started_at, record.model_dump_json()),
            )

    def get_pack(self, *, job_id: str, pack_id: str) -> McpEvidencePack:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM mcp_evidence_packs WHERE pack_id = ? AND job_id = ?",
                (pack_id, job_id),
            ).fetchone()
        if row is None:
            raise KeyError("MCP Evidence Pack not found")
        return self._decode_pack(row["payload_json"])

    def list_packs_for_job(self, *, job_id: str, limit: int = 20) -> list[McpEvidencePack]:
        bounded_limit = max(1, min(limit, 100))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM mcp_evidence_packs WHERE job_id = ? ORDER BY created_at DESC, pack_id DESC LIMIT ?",
                (job_id, bounded_limit),
            ).fetchall()
        return [self._decode_pack(row["payload_json"]) for row in rows]

    def list_calls_for_job(self, *, job_id: str, limit: int = 100) -> list[McpCallRecord]:
        bounded_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM mcp_call_records WHERE job_id = ? ORDER BY started_at DESC, call_id DESC LIMIT ?",
                (job_id, bounded_limit),
            ).fetchall()
        return [McpCallRecord.model_validate_json(row["payload_json"]) for row in rows]

    def delete_for_job(self, job_id: str) -> int:
        with self._connect() as connection:
            pack_count = connection.execute("SELECT COUNT(*) FROM mcp_evidence_packs WHERE job_id = ?", (job_id,)).fetchone()[0]
            call_count = connection.execute("SELECT COUNT(*) FROM mcp_call_records WHERE job_id = ?", (job_id,)).fetchone()[0]
            connection.execute("DELETE FROM mcp_evidence_packs WHERE job_id = ?", (job_id,))
            connection.execute("DELETE FROM mcp_call_records WHERE job_id = ?", (job_id,))
        return int(pack_count) + int(call_count)
