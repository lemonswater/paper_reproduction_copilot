from __future__ import annotations

"""PostgreSQL Artifact Repository 双后端语义测试。

覆盖 Phase 24 已验证的 revision 语义，并在 PostgreSQL 上额外验证并发首次
publish 只产生一个 head：

- 首次 publish revision=1
- 同 sha/backend 重放 revision 不变
- 新 sha revision+1
- backend 迁移 revision+1
- 同 artifact_id 不同 run/path 冲突
- 并发首次 publish 只产生一个 head
- list_for_job 隔离
- Catalog 不包含 absolute_path
"""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.postgres_artifact_repository import (
    PostgresArtifactRepository,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
)


pytestmark = pytest.mark.postgres


@pytest.fixture
def repository(postgres_engine):
    return PostgresArtifactRepository(postgres_engine)


def _descriptor(
    sha256: str,
    size: int,
    *,
    artifact_id: str = "artifact-1",
    run_id: str = "run-1",
    relative_path: str = "reports/final.md",
) -> ArtifactDescriptor:
    return ArtifactDescriptor(
        artifact_id=artifact_id,
        run_id=run_id,
        layer="reports",
        relative_path=relative_path,
        media_type="text/markdown",
        sha256=sha256,
        size_bytes=size,
        producer_node="final_report",
        created_at="2026-07-30T00:00:00+00:00",
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


def test_first_publish_revision_one(repository) -> None:
    published = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )
    assert published.revision == 1


def test_same_version_is_idempotent(repository) -> None:
    repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )
    second = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )
    assert second.revision == 1


def test_new_content_increments_revision(repository) -> None:
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
    assert current.descriptor.sha256 == "b" * 64


def test_backend_migration_increments_revision(
    repository,
) -> None:
    descriptor = _descriptor("a" * 64, 10)
    repository.publish(
        job_id="job-1",
        descriptor=descriptor,
        blob=_blob("a" * 64, 10, "local"),
    )
    current = repository.publish(
        job_id="job-1",
        descriptor=descriptor,
        blob=_blob("a" * 64, 10, "s3"),
    )
    assert current.revision == 2
    assert current.backend == "s3"


def test_conflict_on_different_run(repository) -> None:
    repository.publish(
        job_id="job-1",
        descriptor=_descriptor(
            "a" * 64,
            10,
            run_id="run-1",
        ),
        blob=_blob("a" * 64, 10),
    )
    with pytest.raises(ArtifactIntegrityError):
        repository.publish(
            job_id="job-2",
            descriptor=_descriptor(
                "b" * 64,
                20,
                run_id="run-2",
            ),
            blob=_blob("b" * 64, 20),
        )


def test_concurrent_first_publish_single_head(
    postgres_engine,
) -> None:
    """多个 Worker 并发 publish 同一新 artifact，只产生一个 head。"""

    artifact_id = f"concurrent-{uuid4().hex}"
    sha = "c" * 64

    def publish(_worker_index: int):
        repo = PostgresArtifactRepository(postgres_engine)
        return repo.publish(
            job_id="job-concurrent",
            descriptor=_descriptor(
                sha,
                10,
                artifact_id=artifact_id,
            ),
            blob=_blob(sha, 10),
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(publish, range(8)))

    # 全部成功，revision 都是 1（同 sha/backend 幂等）。
    assert all(r.revision == 1 for r in results)
    assert all(r.descriptor.sha256 == sha for r in results)

    final = PostgresArtifactRepository(
        postgres_engine
    ).find(
        job_id="job-concurrent",
        artifact_id=artifact_id,
    )
    assert final is not None
    assert final.revision == 1


def test_list_for_job_isolation(repository) -> None:
    repository.publish(
        job_id="job-a",
        descriptor=_descriptor(
            "a" * 64,
            10,
            artifact_id="artifact-a",
            relative_path="reports/a.md",
        ),
        blob=_blob("a" * 64, 10),
    )
    repository.publish(
        job_id="job-b",
        descriptor=_descriptor(
            "b" * 64,
            20,
            artifact_id="artifact-b",
            relative_path="reports/b.md",
        ),
        blob=_blob("b" * 64, 20),
    )
    only_a = repository.list_for_job("job-a")
    only_b = repository.list_for_job("job-b")

    assert [a.descriptor.artifact_id for a in only_a] == [
        "artifact-a"
    ]
    assert [b.descriptor.artifact_id for b in only_b] == [
        "artifact-b"
    ]


def test_published_artifact_has_no_absolute_path(
    repository,
) -> None:
    """Catalog 只保存 relative_path，不泄露 absolute_path。"""

    published = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )
    # PublishedArtifact 故意不包含 absolute_path 字段；relative_path 是相对的。
    assert "/" in published.descriptor.relative_path
    assert not hasattr(published, "absolute_path")
    assert not hasattr(published.descriptor, "absolute_path")
