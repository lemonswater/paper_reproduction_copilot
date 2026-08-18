from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.notifications.errors import (
    NotificationConflictError,
    NotificationNotFoundError,
)
from app.notifications.schemas import (
    NotificationProjection,
    NotificationRecord,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteNotificationRepository:
    """单机通知箱；每个方法独立连接，支持 API/SSE 线程并发读取。"""

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
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_id TEXT NOT NULL UNIQUE,
                    source_event_id INTEGER NOT NULL UNIQUE,
                    job_id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (
                        kind IN (
                            'approval_required',
                            'input_required',
                            'job_failed',
                            'job_succeeded',
                            'worker_lost',
                            'job_recovered'
                        )
                    ),
                    severity TEXT NOT NULL CHECK (
                        severity IN ('info','success','warning','error')
                    ),
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    job_version INTEGER,
                    wait_generation INTEGER,
                    expected_node TEXT,
                    operation_kind TEXT,
                    version INTEGER NOT NULL DEFAULT 0,
                    read_at TEXT,
                    superseded_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_notifications_inbox
                ON notifications (
                    superseded_at,
                    read_at,
                    notification_seq
                );

                CREATE INDEX IF NOT EXISTS idx_notifications_job
                ON notifications (job_id, notification_seq);

                CREATE TABLE IF NOT EXISTS notification_projection_meta (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    last_event_id INTEGER NOT NULL CHECK (last_event_id >= 0)
                );

                INSERT OR IGNORE INTO notification_projection_meta (
                    singleton_id,
                    last_event_id
                ) VALUES (1, 0);
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def close(self) -> None:
        return None

    @staticmethod
    def _record(row: sqlite3.Row) -> NotificationRecord:
        return NotificationRecord(
            notification_seq=row["notification_seq"],
            notification_id=row["notification_id"],
            source_event_id=row["source_event_id"],
            job_id=row["job_id"],
            kind=row["kind"],
            severity=row["severity"],
            title=row["title"],
            message=row["message"],
            job_version=row["job_version"],
            wait_generation=row["wait_generation"],
            expected_node=row["expected_node"],
            operation_kind=row["operation_kind"],
            version=row["version"],
            read_at=row["read_at"],
            superseded_at=row["superseded_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def projection_cursor(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT last_event_id
                FROM notification_projection_meta
                WHERE singleton_id = 1
                """
            ).fetchone()
        return int(row["last_event_id"])

    def apply_projection(
        self,
        projection: NotificationProjection,
    ) -> bool:
        """通知、失效变更和 cursor 在一个 SQLite 事务中提交。"""

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor_row = connection.execute(
                """
                SELECT last_event_id
                FROM notification_projection_meta
                WHERE singleton_id = 1
                """
            ).fetchone()
            cursor = int(cursor_row["last_event_id"])
            if projection.source_event_id <= cursor:
                connection.commit()
                return False

            updated_at = _utc_now()

            if projection.supersede_operation_notifications:
                connection.execute(
                    """
                    UPDATE notifications
                    SET superseded_at = ?,
                        updated_at = ?,
                        version = version + 1
                    WHERE job_id = ?
                      AND kind IN ('approval_required','input_required')
                      AND superseded_at IS NULL
                    """,
                    (
                        projection.event_created_at,
                        updated_at,
                        projection.job_id,
                    ),
                )

            if projection.supersede_worker_lost:
                connection.execute(
                    """
                    UPDATE notifications
                    SET superseded_at = ?,
                        updated_at = ?,
                        version = version + 1
                    WHERE job_id = ?
                      AND kind = 'worker_lost'
                      AND superseded_at IS NULL
                    """,
                    (
                        projection.event_created_at,
                        updated_at,
                        projection.job_id,
                    ),
                )

            draft = projection.notification
            if draft is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO notifications (
                        notification_id,
                        source_event_id,
                        job_id,
                        kind,
                        severity,
                        title,
                        message,
                        job_version,
                        wait_generation,
                        expected_node,
                        operation_kind,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft.notification_id,
                        draft.source_event_id,
                        draft.job_id,
                        draft.kind,
                        draft.severity,
                        draft.title,
                        draft.message,
                        draft.job_version,
                        draft.wait_generation,
                        draft.expected_node,
                        draft.operation_kind,
                        draft.created_at,
                        updated_at,
                    ),
                )

            connection.execute(
                """
                UPDATE notification_projection_meta
                SET last_event_id = ?
                WHERE singleton_id = 1
                  AND last_event_id < ?
                """,
                (
                    projection.source_event_id,
                    projection.source_event_id,
                ),
            )
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(
        self,
        notification_id: str,
    ) -> NotificationRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM notifications
                WHERE notification_id = ?
                """,
                (notification_id,),
            ).fetchone()
        if row is None:
            raise NotificationNotFoundError(
                f"notification 不存在：{notification_id}"
            )
        return self._record(row)

    def list_after(
        self,
        *,
        after_sequence: int = 0,
        unread_only: bool = False,
        limit: int = 100,
    ) -> list[NotificationRecord]:
        clauses = ["notification_seq > ?"]
        parameters: list[object] = [max(0, after_sequence)]
        if unread_only:
            clauses.extend(
                ["read_at IS NULL", "superseded_at IS NULL"]
            )
        parameters.append(max(1, min(limit, 500)))
        where = " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM notifications
                WHERE {where}
                ORDER BY notification_seq ASC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [self._record(row) for row in rows]

    def unread_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM notifications
                WHERE read_at IS NULL
                  AND superseded_at IS NULL
                """
            ).fetchone()
        return int(row["total"])

    def has_active_kind(
        self,
        *,
        job_id: str,
        kind: str,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM notifications
                WHERE job_id = ?
                  AND kind = ?
                  AND superseded_at IS NULL
                LIMIT 1
                """,
                (job_id, kind),
            ).fetchone()
        return row is not None

    def mark_read(
        self,
        *,
        notification_id: str,
        expected_version: int,
    ) -> NotificationRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM notifications
                WHERE notification_id = ?
                """,
                (notification_id,),
            ).fetchone()
            if row is None:
                raise NotificationNotFoundError(
                    f"notification 不存在：{notification_id}"
                )

            # mark read 是幂等低风险 mutation；已经读取时直接返回。
            if row["read_at"] is not None:
                connection.commit()
                return self._record(row)

            if int(row["version"]) != expected_version:
                raise NotificationConflictError(
                    "notification version 已变化"
                )

            now = _utc_now()
            connection.execute(
                """
                UPDATE notifications
                SET read_at = ?,
                    updated_at = ?,
                    version = version + 1
                WHERE notification_id = ?
                  AND version = ?
                """,
                (
                    now,
                    now,
                    notification_id,
                    expected_version,
                ),
            )
            updated = connection.execute(
                """
                SELECT * FROM notifications
                WHERE notification_id = ?
                """,
                (notification_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_all_read(
        self,
        *,
        through_sequence: int,
    ) -> int:
        now = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE notifications
                SET read_at = ?,
                    updated_at = ?,
                    version = version + 1
                WHERE notification_seq <= ?
                  AND read_at IS NULL
                  AND superseded_at IS NULL
                """,
                (now, now, max(0, through_sequence)),
            )
        return int(cursor.rowcount)

    def delete_for_job(self, job_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM notifications
                WHERE job_id = ?
                """,
                (job_id,),
            )
        return int(cursor.rowcount)
