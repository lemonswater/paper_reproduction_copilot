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


def test_publisher_survives_source_removal(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    run_root = tmp_path / "runs" / "run-1"
    report = run_root / "reports/final.md"
    report.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    report.write_text(
        "final report",
        encoding="utf-8",
    )

    state = {
        "run_id": "run-1",
        "run_dir": str(run_root),
    }
    record = build_artifact_record(
        state=state,
        path=report,
        producer_node="test",
    )

    job_store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    job_store.initialize()
    job, _ = job_store.submit(
        job_id="job-1",
        idempotency_key="submit-1",
        thread_id="thread-1",
        run_id="run-1",
        run_dir=str(run_root),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="1"),
        max_attempts=3,
    )

    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    blob_store = LocalBlobStore(
        tmp_path / "blob-store"
    )
    publisher = ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    )

    first = publisher.publish(
        job=job,
        records=[record],
    )
    second = publisher.publish(
        job=job,
        records=[record],
    )

    assert first.published_count == 1
    assert second.reused_count == 1

    published = repository.find(
        job_id=job.job_id,
        artifact_id=record.artifact_id,
    )
    assert published is not None
    report.unlink()

    opened = blob_store.open(
        published.object_key
    )
    try:
        assert (
            opened.body.read()
            == b"final report"
        )
    finally:
        opened.body.close()
