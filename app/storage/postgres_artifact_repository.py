from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine, RowMapping

from app.persistence.database import (
    build_engine,
    database_clock,
)
from app.persistence.tables import (
    artifact_heads,
    artifact_versions,
)
from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


class PostgresArtifactRepository:
    def __init__(self, engine: Engine | None = None):
        self.engine = engine or build_engine()

    def initialize(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(sa.text("SELECT 1"))

    def _joined(self) -> sa.Select:
        return sa.select(
            artifact_versions,
            artifact_heads.c.revision,
        ).join(
            artifact_heads,
            sa.and_(
                artifact_heads.c.artifact_id
                == artifact_versions.c.artifact_id,
                artifact_heads.c.current_sha256
                == artifact_versions.c.sha256,
                artifact_heads.c.current_backend
                == artifact_versions.c.backend,
            ),
        )

    def _to_published(
        self,
        row: RowMapping,
    ) -> PublishedArtifact:
        return PublishedArtifact(
            job_id=row["job_id"],
            descriptor=ArtifactDescriptor(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                layer=row["layer"],
                relative_path=row["relative_path"],
                media_type=row["media_type"],
                sha256=row["sha256"],
                size_bytes=row["size_bytes"],
                producer_node=row["producer_node"],
                created_at=row["artifact_created_at"],
            ),
            backend=row["backend"],
            object_key=row["object_key"],
            etag=row["etag"],
            object_version_id=row[
                "object_version_id"
            ],
            revision=row["revision"],
            published_at=row[
                "published_at"
            ].isoformat(),
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
            or descriptor.size_bytes != blob.size_bytes
        ):
            raise ArtifactIntegrityError(
                "Blob 与 ArtifactDescriptor 不一致"
            )

        with self.engine.begin() as connection:
            current = database_clock(connection)
            # 相同 artifact_id 串行；不同 Artifact 不互相阻塞。
            connection.execute(
                sa.select(
                    sa.func.pg_advisory_xact_lock(
                        sa.func.hashtextextended(
                            descriptor.artifact_id,
                            0,
                        )
                    )
                )
            )
            head = connection.execute(
                sa.select(artifact_heads)
                .where(
                    artifact_heads.c.artifact_id
                    == descriptor.artifact_id
                )
                .with_for_update()
            ).mappings().one_or_none()

            if head is not None and (
                head["job_id"] != job_id
                or head["run_id"] != descriptor.run_id
                or head["relative_path"]
                != descriptor.relative_path
            ):
                raise ArtifactIntegrityError(
                    "artifact_id 身份发生冲突"
                )

            version_values = {
                "artifact_id": descriptor.artifact_id,
                "sha256": descriptor.sha256,
                "backend": blob.backend,
                "job_id": job_id,
                "run_id": descriptor.run_id,
                "layer": descriptor.layer,
                "relative_path": descriptor.relative_path,
                "media_type": descriptor.media_type,
                "size_bytes": descriptor.size_bytes,
                "producer_node": descriptor.producer_node,
                "artifact_created_at": descriptor.created_at,
                "object_key": blob.object_key,
                "etag": blob.etag,
                "object_version_id": blob.version_id,
                "published_at": current,
            }
            connection.execute(
                insert(artifact_versions)
                .values(**version_values)
                .on_conflict_do_nothing(
                    index_elements=[
                        artifact_versions.c.artifact_id,
                        artifact_versions.c.sha256,
                        artifact_versions.c.backend,
                    ]
                )
            )

            existing_version = connection.execute(
                sa.select(artifact_versions).where(
                    artifact_versions.c.artifact_id
                    == descriptor.artifact_id,
                    artifact_versions.c.sha256
                    == descriptor.sha256,
                    artifact_versions.c.backend
                    == blob.backend,
                )
            ).mappings().one()
            if existing_version["object_key"] != blob.object_key:
                raise ArtifactIntegrityError(
                    "相同 Artifact version 对应不同 object_key"
                )

            same_head = (
                head is not None
                and head["current_sha256"]
                == descriptor.sha256
                and head["current_backend"] == blob.backend
            )
            if head is None:
                connection.execute(
                    artifact_heads.insert().values(
                        artifact_id=descriptor.artifact_id,
                        job_id=job_id,
                        run_id=descriptor.run_id,
                        relative_path=descriptor.relative_path,
                        current_sha256=descriptor.sha256,
                        current_backend=blob.backend,
                        revision=1,
                        updated_at=current,
                    )
                )
            elif not same_head:
                connection.execute(
                    artifact_heads.update()
                    .where(
                        artifact_heads.c.artifact_id
                        == descriptor.artifact_id
                    )
                    .values(
                        current_sha256=descriptor.sha256,
                        current_backend=blob.backend,
                        revision=(
                            artifact_heads.c.revision + 1
                        ),
                        updated_at=current,
                    )
                )

            row = connection.execute(
                self._joined().where(
                    artifact_heads.c.artifact_id
                    == descriptor.artifact_id
                )
            ).mappings().one()
            return self._to_published(row)

    def find(
        self,
        *,
        job_id: str,
        artifact_id: str,
    ) -> PublishedArtifact | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                self._joined().where(
                    artifact_heads.c.job_id == job_id,
                    artifact_heads.c.artifact_id
                    == artifact_id,
                )
            ).mappings().one_or_none()
        return (
            None
            if row is None
            else self._to_published(row)
        )

    def list_for_job(
        self,
        job_id: str,
    ) -> list[PublishedArtifact]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                self._joined()
                .where(artifact_heads.c.job_id == job_id)
                .order_by(
                    artifact_versions.c.layer,
                    artifact_versions.c.relative_path,
                )
            ).mappings().all()
        return [self._to_published(row) for row in rows]
