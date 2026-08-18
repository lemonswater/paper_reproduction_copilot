from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)
from app.retention.schemas import BlobReference


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


class SqliteArtifactRepository:
    """
    Artifact versions 与当前 head 分表。

    同一个 artifact_id 可以保留多个 sha256/backend revision。
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
        connection.execute(
            "PRAGMA journal_mode=WAL"
        )
        connection.execute(
            "PRAGMA synchronous=NORMAL"
        )
        connection.execute(
            "PRAGMA busy_timeout=30000"
        )
        connection.execute(
            "PRAGMA foreign_keys=ON"
        )
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    artifact_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    backend TEXT NOT NULL,

                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    producer_node TEXT NOT NULL,
                    artifact_created_at TEXT NOT NULL,

                    object_key TEXT NOT NULL,
                    etag TEXT,
                    object_version_id TEXT,
                    published_at REAL NOT NULL,

                    PRIMARY KEY (
                        artifact_id,
                        sha256,
                        backend
                    )
                );

                CREATE TABLE IF NOT EXISTS artifact_heads (
                    artifact_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    current_sha256 TEXT NOT NULL,
                    current_backend TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    updated_at REAL NOT NULL,

                    FOREIGN KEY (
                        artifact_id,
                        current_sha256,
                        current_backend
                    )
                    REFERENCES artifact_versions (
                        artifact_id,
                        sha256,
                        backend
                    )
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_artifact_heads_job_path
                ON artifact_heads(
                    job_id,
                    relative_path
                );

                CREATE INDEX IF NOT EXISTS
                idx_artifact_heads_job
                ON artifact_heads(
                    job_id,
                    artifact_id
                );
                """
            )

    def _joined_select(self) -> str:
        return """
            SELECT
                v.*,
                h.revision
            FROM artifact_heads AS h
            JOIN artifact_versions AS v
              ON v.artifact_id = h.artifact_id
             AND v.sha256 = h.current_sha256
             AND v.backend = h.current_backend
        """

    def _row_to_published(
        self,
        row: sqlite3.Row,
    ) -> PublishedArtifact:
        return PublishedArtifact(
            job_id=row["job_id"],
            descriptor=ArtifactDescriptor(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                layer=row["layer"],
                relative_path=(
                    row["relative_path"]
                ),
                media_type=row["media_type"],
                sha256=row["sha256"],
                size_bytes=row["size_bytes"],
                producer_node=(
                    row["producer_node"]
                ),
                created_at=(
                    row["artifact_created_at"]
                ),
            ),
            backend=row["backend"],
            object_key=row["object_key"],
            etag=row["etag"],
            object_version_id=(
                row["object_version_id"]
            ),
            revision=row["revision"],
            published_at=_iso(
                row["published_at"]
            ),
        )

    def publish(
        self,
        *,
        job_id: str,
        descriptor: ArtifactDescriptor,
        blob: BlobStat,
    ) -> PublishedArtifact:
        if (
            descriptor.sha256 != blob.sha256
            or descriptor.size_bytes
            != blob.size_bytes
        ):
            raise ArtifactIntegrityError(
                "Blob 与 ArtifactDescriptor 不一致"
            )

        now = time.time()
        connection = self._connect()
        try:
            connection.execute(
                "BEGIN IMMEDIATE"
            )
            head = connection.execute(
                """
                SELECT *
                FROM artifact_heads
                WHERE artifact_id = ?
                """,
                (descriptor.artifact_id,),
            ).fetchone()

            if head is not None and (
                head["job_id"] != job_id
                or head["run_id"]
                != descriptor.run_id
                or head["relative_path"]
                != descriptor.relative_path
            ):
                raise ArtifactIntegrityError(
                    "artifact_id 身份发生冲突"
                )

            existing_version = connection.execute(
                """
                SELECT *
                FROM artifact_versions
                WHERE artifact_id = ?
                  AND sha256 = ?
                  AND backend = ?
                """,
                (
                    descriptor.artifact_id,
                    descriptor.sha256,
                    blob.backend,
                ),
            ).fetchone()
            if (
                existing_version is not None
                and existing_version["object_key"]
                != blob.object_key
            ):
                raise ArtifactIntegrityError(
                    "相同 Artifact version "
                    "对应不同 object_key"
                )

            connection.execute(
                """
                INSERT OR IGNORE INTO artifact_versions (
                    artifact_id,
                    sha256,
                    backend,
                    job_id,
                    run_id,
                    layer,
                    relative_path,
                    media_type,
                    size_bytes,
                    producer_node,
                    artifact_created_at,
                    object_key,
                    etag,
                    object_version_id,
                    published_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    descriptor.artifact_id,
                    descriptor.sha256,
                    blob.backend,
                    job_id,
                    descriptor.run_id,
                    descriptor.layer,
                    descriptor.relative_path,
                    descriptor.media_type,
                    descriptor.size_bytes,
                    descriptor.producer_node,
                    descriptor.created_at,
                    blob.object_key,
                    blob.etag,
                    blob.version_id,
                    now,
                ),
            )

            same_head = (
                head is not None
                and head["current_sha256"]
                == descriptor.sha256
                and head["current_backend"]
                == blob.backend
            )
            if head is None:
                connection.execute(
                    """
                    INSERT INTO artifact_heads (
                        artifact_id,
                        job_id,
                        run_id,
                        relative_path,
                        current_sha256,
                        current_backend,
                        revision,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        descriptor.artifact_id,
                        job_id,
                        descriptor.run_id,
                        descriptor.relative_path,
                        descriptor.sha256,
                        blob.backend,
                        now,
                    ),
                )
            elif not same_head:
                connection.execute(
                    """
                    UPDATE artifact_heads
                    SET current_sha256 = ?,
                        current_backend = ?,
                        revision = revision + 1,
                        updated_at = ?
                    WHERE artifact_id = ?
                    """,
                    (
                        descriptor.sha256,
                        blob.backend,
                        now,
                        descriptor.artifact_id,
                    ),
                )

            row = connection.execute(
                self._joined_select()
                + """
                  WHERE h.artifact_id = ?
                """,
                (descriptor.artifact_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_published(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def find(
        self,
        *,
        job_id: str,
        artifact_id: str,
    ) -> PublishedArtifact | None:
        with self._connect() as connection:
            row = connection.execute(
                self._joined_select()
                + """
                  WHERE h.job_id = ?
                    AND h.artifact_id = ?
                """,
                (
                    job_id,
                    artifact_id,
                ),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_published(row)

    def list_for_job(
        self,
        job_id: str,
    ) -> list[PublishedArtifact]:
        with self._connect() as connection:
            rows = connection.execute(
                self._joined_select()
                + """
                  WHERE h.job_id = ?
                  ORDER BY
                    v.layer,
                    v.relative_path
                """,
                (job_id,),
            ).fetchall()
        return [
            self._row_to_published(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Phase 35: Retention methods
    # ------------------------------------------------------------------

    def list_blob_references_for_job(
        self,
        job_id: str,
    ) -> list[BlobReference]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT backend, object_key, sha256, size_bytes
                FROM artifact_versions
                WHERE job_id = ?
                ORDER BY backend, object_key
                """,
                (job_id,),
            ).fetchall()
        return [
            BlobReference(
                backend=row["backend"],
                object_key=row["object_key"],
                sha256=row["sha256"],
                size_bytes=row["size_bytes"],
            )
            for row in rows
        ]

    def delete_job_artifacts(self, job_id: str) -> int:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM artifact_heads WHERE job_id = ?",
                (job_id,),
            )
            deleted = connection.execute(
                "DELETE FROM artifact_versions WHERE job_id = ?",
                (job_id,),
            ).rowcount
            connection.commit()
            return int(deleted)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM artifact_versions
                WHERE backend = ? AND object_key = ?
                """,
                (backend, object_key),
            ).fetchone()
        return int(row["count"])