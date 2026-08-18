from __future__ import annotations

from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
)


def _descriptor(
    sha256: str,
    size: int,
) -> ArtifactDescriptor:
    return ArtifactDescriptor(
        artifact_id="artifact-1",
        run_id="run-1",
        layer="reports",
        relative_path="reports/final.md",
        media_type="text/markdown",
        sha256=sha256,
        size_bytes=size,
        producer_node="final_report",
        created_at=(
            "2026-07-30T00:00:00+00:00"
        ),
    )


def _blob(
    sha256: str,
    size: int,
    backend: str = "local",
) -> BlobStat:
    return BlobStat(
        backend=backend,
        object_key=f"sha256/{sha256}",
        size_bytes=size,
        sha256=sha256,
        etag="etag",
    )


def test_publish_same_version_is_idempotent(
    tmp_path,
) -> None:
    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    repository.initialize()

    first = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )
    second = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )

    assert first.revision == 1
    assert second.revision == 1


def test_new_content_increments_revision(
    tmp_path,
) -> None:
    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    repository.initialize()
    repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )

    current = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("b" * 64, 20),
        blob=_blob("b" * 64, 20),
    )

    assert current.revision == 2
    assert (
        current.descriptor.sha256
        == "b" * 64
    )


def test_backend_migration_increments_revision(
    tmp_path,
) -> None:
    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    repository.initialize()
    descriptor = _descriptor(
        "a" * 64,
        10,
    )
    repository.publish(
        job_id="job-1",
        descriptor=descriptor,
        blob=_blob(
            "a" * 64,
            10,
            "local",
        ),
    )

    current = repository.publish(
        job_id="job-1",
        descriptor=descriptor,
        blob=_blob(
            "a" * 64,
            10,
            "s3",
        ),
    )

    assert current.revision == 2
    assert current.backend == "s3"