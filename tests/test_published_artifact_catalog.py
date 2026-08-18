from __future__ import annotations

from app.config import settings
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.catalog import (
    BlobStoreRegistry,
    PublishedArtifactCatalog,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.storage.publisher import (
    ArtifactPublisher,
)
from app.tools.artifact_tools import (
    build_artifact_record,
)
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
)


def test_catalog_lists_and_opens_published_blob(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    run_root = tmp_path / "runs/run-catalog"
    source = run_root / "reports/final.md"
    source.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    source.write_text(
        "catalog artifact",
        encoding="utf-8",
    )

    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    job, _ = store.submit(
        job_id="job-catalog",
        idempotency_key="catalog-submit",
        thread_id="thread-catalog",
        run_id="run-catalog",
        run_dir=str(run_root),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="catalog"),
        max_attempts=3,
    )
    record = build_artifact_record(
        state={
            "run_id": job.run_id,
            "run_dir": job.run_dir,
        },
        path=source,
        producer_node="test",
    )

    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    blob_store = LocalBlobStore(
        tmp_path / "blob-store"
    )
    ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    ).publish(
        job=job,
        records=[record],
    )
    source.unlink()

    catalog = PublishedArtifactCatalog(
        repository=repository,
        registry=BlobStoreRegistry(
            [blob_store]
        ),
    )
    views = catalog.list_views(job)
    assert [
        item.artifact_id
        for item in views
    ] == [record.artifact_id]

    opened = catalog.open(
        job=job,
        artifact_id=record.artifact_id,
    )
    try:
        assert (
            opened.blob.body.read()
            == b"catalog artifact"
        )
    finally:
        opened.blob.body.close()
