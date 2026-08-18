"""SQLite Chat Store：每个 Job 拥有独立聊天序列。"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.chat.errors import ChatConflictError, ChatMemoryConflict
from app.chat.schemas import (
    ChatCitation,
    ChatMessage,
    ChatToolTraceSummary,
    ConversationMemory,
)


class ChatRepository(Protocol):
    def initialize(self) -> None:
        ...

    def ping(self) -> None:
        ...

    def list_messages(
        self,
        *,
        job_id: str,
        after_sequence: int,
        limit: int,
    ) -> list[ChatMessage]:
        ...

    def list_recent_messages(
        self,
        *,
        job_id: str,
        limit: int,
    ) -> list[ChatMessage]:
        ...

    def list_messages_range(
        self,
        *,
        job_id: str,
        start_sequence: int,
        end_sequence: int,
        limit: int,
    ) -> list[ChatMessage]:
        ...

    def latest_sequence(self, job_id: str) -> int:
        ...

    def find_exchange(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        request_sha256: str,
    ) -> tuple[ChatMessage, ChatMessage] | None:
        ...

    def append_exchange(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        request_sha256: str,
        question: str,
        answer: str,
        citations: Sequence[ChatCitation],
        tool_trace: ChatToolTraceSummary | None = None,
    ) -> tuple[ChatMessage, ChatMessage, bool]:
        ...

    def get_latest_memory(
        self,
        job_id: str,
    ) -> ConversationMemory | None:
        ...

    def save_memory(
        self,
        *,
        memory: ConversationMemory,
        expected_parent_memory_id: str | None,
    ) -> tuple[ConversationMemory, bool]:
        ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteChatRepository:
    """单主机 Chat Store；每个操作使用独立连接，便于 FastAPI 线程池调用。"""

    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    citations_json TEXT NOT NULL DEFAULT '[]',
                    tool_trace_json TEXT,
                    reply_to TEXT,
                    request_key TEXT,
                    request_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(job_id, sequence),
                    UNIQUE(job_id, request_key)
                );

                CREATE INDEX IF NOT EXISTS idx_chat_job_sequence
                ON chat_messages(job_id, sequence);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_reply_to
                ON chat_messages(reply_to)
                WHERE reply_to IS NOT NULL;

                CREATE TABLE IF NOT EXISTS chat_memory_versions (
                    memory_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    covered_from_sequence INTEGER NOT NULL,
                    covered_through_sequence INTEGER NOT NULL,
                    delta_messages_sha256 TEXT NOT NULL,
                    parent_memory_id TEXT,
                    parent_memory_sha256 TEXT,
                    body_json TEXT NOT NULL,
                    memory_sha256 TEXT NOT NULL UNIQUE,
                    prompt_version TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    structured_method TEXT NOT NULL,
                    strict INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(job_id, version),
                    UNIQUE(job_id, covered_through_sequence)
                );

                CREATE TABLE IF NOT EXISTS chat_memory_heads (
                    job_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(memory_id)
                        REFERENCES chat_memory_versions(memory_id)
                );

                CREATE INDEX IF NOT EXISTS idx_chat_memory_job_version
                ON chat_memory_versions(job_id, version);
                """
            )

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(chat_messages)"
                ).fetchall()
            }
            if "tool_trace_json" not in columns:
                connection.execute(
                    "ALTER TABLE chat_messages ADD COLUMN tool_trace_json TEXT"
                )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    @staticmethod
    def _message(row: sqlite3.Row) -> ChatMessage:
        raw_trace = row["tool_trace_json"] if "tool_trace_json" in row.keys() else None
        return ChatMessage(
            message_id=row["message_id"],
            job_id=row["job_id"],
            sequence=row["sequence"],
            role=row["role"],
            content=row["content"],
            citations=[
                ChatCitation.model_validate(item)
                for item in json.loads(row["citations_json"])
            ],
            tool_trace=(
                None
                if raw_trace is None
                else ChatToolTraceSummary.model_validate_json(raw_trace)
            ),
            reply_to=row["reply_to"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _memory(row: sqlite3.Row) -> ConversationMemory:
        return ConversationMemory(
            memory_id=row["memory_id"],
            job_id=row["job_id"],
            version=row["version"],
            covered_from_sequence=row["covered_from_sequence"],
            covered_through_sequence=row["covered_through_sequence"],
            delta_messages_sha256=row["delta_messages_sha256"],
            parent_memory_id=row["parent_memory_id"],
            parent_memory_sha256=row["parent_memory_sha256"],
            body=json.loads(row["body_json"]),
            memory_sha256=row["memory_sha256"],
            prompt_version=row["prompt_version"],
            model_name=row["model_name"],
            structured_method=row["structured_method"],
            strict=bool(row["strict"]),
            created_at=row["created_at"],
        )

    def list_messages(
        self,
        *,
        job_id: str,
        after_sequence: int,
        limit: int,
    ) -> list[ChatMessage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM chat_messages
                WHERE job_id = ? AND sequence > ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (job_id, after_sequence, limit),
            ).fetchall()
        return [self._message(row) for row in rows]

    def list_recent_messages(
        self,
        *,
        job_id: str,
        limit: int,
    ) -> list[ChatMessage]:
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM chat_messages
                WHERE job_id = ?
                ORDER BY sequence DESC
                LIMIT ?
                """,
                (job_id, bounded),
            ).fetchall()
        # SQL 为了取 newest 使用 DESC；Prompt 必须恢复时间正序。
        return [self._message(row) for row in reversed(rows)]

    def list_messages_range(
        self,
        *,
        job_id: str,
        start_sequence: int,
        end_sequence: int,
        limit: int,
    ) -> list[ChatMessage]:
        if start_sequence < 1 or end_sequence < start_sequence:
            return []
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM chat_messages
                WHERE job_id = ?
                  AND sequence BETWEEN ? AND ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (job_id, start_sequence, end_sequence, bounded),
            ).fetchall()
        return [self._message(row) for row in rows]

    def latest_sequence(self, job_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(sequence), 0) AS latest
                FROM chat_messages
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        return int(row["latest"])

    def _exchange_from_user_row(
        self,
        connection: sqlite3.Connection,
        user_row: sqlite3.Row,
        request_sha256: str,
    ) -> tuple[ChatMessage, ChatMessage]:
        if user_row["request_sha256"] != request_sha256:
            raise ChatConflictError(
                "同一 Idempotency-Key 不能用于不同问题"
            )
        assistant_row = connection.execute(
            "SELECT * FROM chat_messages WHERE reply_to = ?",
            (user_row["message_id"],),
        ).fetchone()
        if assistant_row is None:
            raise ChatConflictError(
                "Chat exchange 不完整，需要人工检查数据库"
            )
        return self._message(user_row), self._message(assistant_row)

    def find_exchange(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        request_sha256: str,
    ) -> tuple[ChatMessage, ChatMessage] | None:
        with self._connect() as connection:
            user_row = connection.execute(
                """
                SELECT * FROM chat_messages
                WHERE job_id = ? AND request_key = ?
                """,
                (job_id, idempotency_key),
            ).fetchone()
            if user_row is None:
                return None
            return self._exchange_from_user_row(
                connection,
                user_row,
                request_sha256,
            )

    def append_exchange(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        request_sha256: str,
        question: str,
        answer: str,
        citations: Sequence[ChatCitation],
        tool_trace: ChatToolTraceSummary | None = None,
    ) -> tuple[ChatMessage, ChatMessage, bool]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM chat_messages
                WHERE job_id = ? AND request_key = ?
                """,
                (job_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                user, assistant = self._exchange_from_user_row(
                    connection,
                    existing,
                    request_sha256,
                )
                connection.commit()
                return user, assistant, False

            next_sequence = connection.execute(
                """
                SELECT COALESCE(MAX(sequence), 0) + 1
                FROM chat_messages
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()[0]
            created_at = _now()
            user_id = f"chat-user-{uuid4().hex}"
            assistant_id = f"chat-assistant-{uuid4().hex}"

            connection.execute(
                """
                INSERT INTO chat_messages (
                    message_id, job_id, sequence, role, content,
                    citations_json, tool_trace_json, reply_to, request_key,
                    request_sha256, created_at
                ) VALUES (?, ?, ?, 'user', ?, '[]', NULL, NULL, ?, ?, ?)
                """,
                (
                    user_id,
                    job_id,
                    next_sequence,
                    question,
                    idempotency_key,
                    request_sha256,
                    created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO chat_messages (
                    message_id, job_id, sequence, role, content,
                    citations_json, tool_trace_json, reply_to, request_key,
                    request_sha256, created_at
                ) VALUES (?, ?, ?, 'assistant', ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (
                    assistant_id,
                    job_id,
                    next_sequence + 1,
                    answer,
                    json.dumps(
                        [item.model_dump() for item in citations],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    (
                        None
                        if tool_trace is None
                        else tool_trace.model_dump_json()
                    ),
                    user_id,
                    created_at,
                ),
            )
            user_row = connection.execute(
                "SELECT * FROM chat_messages WHERE message_id = ?",
                (user_id,),
            ).fetchone()
            assistant_row = connection.execute(
                "SELECT * FROM chat_messages WHERE message_id = ?",
                (assistant_id,),
            ).fetchone()
            connection.commit()
            assert user_row is not None and assistant_row is not None
            return (
                self._message(user_row),
                self._message(assistant_row),
                True,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Phase 36: Memory methods
    # ------------------------------------------------------------------

    def get_latest_memory(
        self,
        job_id: str,
    ) -> ConversationMemory | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT versions.*
                FROM chat_memory_heads AS heads
                JOIN chat_memory_versions AS versions
                  ON versions.memory_id = heads.memory_id
                WHERE heads.job_id = ?
                """,
                (job_id,),
            ).fetchone()
        return None if row is None else self._memory(row)

    def save_memory(
        self,
        *,
        memory: ConversationMemory,
        expected_parent_memory_id: str | None,
    ) -> tuple[ConversationMemory, bool]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            head = connection.execute(
                """
                SELECT versions.*
                FROM chat_memory_heads AS heads
                JOIN chat_memory_versions AS versions
                  ON versions.memory_id = heads.memory_id
                WHERE heads.job_id = ?
                """,
                (memory.job_id,),
            ).fetchone()

            # 两个请求可能基于相同 parent 同时压缩同一 cutoff。
            # 第一个成功后，第二个返回数据库中已接受的版本，不覆盖它。
            existing = connection.execute(
                """
                SELECT * FROM chat_memory_versions
                WHERE job_id = ? AND covered_through_sequence = ?
                """,
                (memory.job_id, memory.covered_through_sequence),
            ).fetchone()
            if existing is not None:
                if (
                    existing["delta_messages_sha256"]
                    != memory.delta_messages_sha256
                    or existing["parent_memory_id"]
                    != expected_parent_memory_id
                ):
                    raise ChatMemoryConflict(
                        "相同 Memory cutoff 对应不同输入身份"
                    )
                latest_row = connection.execute(
                    """
                    SELECT versions.*
                    FROM chat_memory_heads AS heads
                    JOIN chat_memory_versions AS versions
                      ON versions.memory_id = heads.memory_id
                    WHERE heads.job_id = ?
                    """,
                    (memory.job_id,),
                ).fetchone()
                connection.commit()
                assert latest_row is not None
                return self._memory(latest_row), False

            current_parent = (
                head["memory_id"] if head is not None else None
            )
            if current_parent != expected_parent_memory_id:
                raise ChatMemoryConflict(
                    "Memory parent 已变化，请基于最新版本重新压缩"
                )

            expected_version = 1 if head is None else int(head["version"]) + 1
            expected_from = (
                1
                if head is None
                else int(head["covered_through_sequence"]) + 1
            )
            if (
                memory.version != expected_version
                or memory.covered_from_sequence != expected_from
                or memory.parent_memory_id != current_parent
            ):
                raise ChatMemoryConflict("Memory version/range fencing 失败")

            connection.execute(
                """
                INSERT INTO chat_memory_versions (
                    memory_id, job_id, version,
                    covered_from_sequence, covered_through_sequence,
                    delta_messages_sha256,
                    parent_memory_id, parent_memory_sha256,
                    body_json, memory_sha256,
                    prompt_version, model_name,
                    structured_method, strict, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.memory_id,
                    memory.job_id,
                    memory.version,
                    memory.covered_from_sequence,
                    memory.covered_through_sequence,
                    memory.delta_messages_sha256,
                    memory.parent_memory_id,
                    memory.parent_memory_sha256,
                    json.dumps(
                        memory.body.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    memory.memory_sha256,
                    memory.prompt_version,
                    memory.model_name,
                    memory.structured_method,
                    int(memory.strict),
                    memory.created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO chat_memory_heads (
                    job_id, memory_id, version, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    memory_id = excluded.memory_id,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    memory.job_id,
                    memory.memory_id,
                    memory.version,
                    memory.created_at,
                ),
            )
            connection.commit()
            return memory, True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Phase 35/36: Retention methods
    # ------------------------------------------------------------------

    def delete_job_messages(self, job_id: str) -> int:
        """删除一个 Job 的全部 Chat durable data（messages + memory）。"""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            # head 外键引用 version，必须先删 head。
            connection.execute(
                "DELETE FROM chat_memory_heads WHERE job_id = ?",
                (job_id,),
            )
            connection.execute(
                "DELETE FROM chat_memory_versions WHERE job_id = ?",
                (job_id,),
            )
            deleted = connection.execute(
                "DELETE FROM chat_messages WHERE job_id = ?",
                (job_id,),
            ).rowcount
            connection.commit()
            return int(deleted)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
