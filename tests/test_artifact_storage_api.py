from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.config import settings
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.service import JobService
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
    FakeWorkspaceSnapshotter,
    setup_local_execution_profile,
)


def test_api_downloads_published_blob_after_source_deleted(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    setup_local_execution_profile(tmp_path, monkeypatch)

    job_service = JobService(
        SqliteJobStore(
            tmp_path / "jobs.sqlite"
        ),
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    job, _ = job_service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id=(
                settings.default_execution_profile
            ),
        ),
        thread_id="artifact-api",
        idempotency_key="artifact-api",
    )
    # JobService 生成自己的 run_dir，所以测试文件要移动到该目录。
    actual_source = (
        tmp_path
        / "runs"
        / job.run_id
        / "reports"
        / "final.md"
    )
    actual_source.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    actual_source.write_text(
        "durable artifact",
        encoding="utf-8",
    )
    record = build_artifact_record(
        state={
            "run_id": job.run_id,
            "run_dir": job.run_dir,
        },
        path=actual_source,
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
    catalog = PublishedArtifactCatalog(
        repository=repository,
        registry=BlobStoreRegistry(
            [blob_store]
        ),
    )
    actual_source.unlink()

    app = create_api_app(
        job_service=job_service,
        artifact_catalog=catalog,
        api_token="test-token",
    )
    with TestClient(app) as client:
        response = client.get(
            (
                f"/v1/jobs/{job.job_id}"
                "/artifacts/"
                f"{record.artifact_id}"
                "/content"
            ),
            headers={
                "Authorization": (
                    "Bearer test-token"
                )
            },
        )

    assert response.status_code == 200
    assert response.content == (
        b"durable artifact"
    )
    assert response.headers["content-type"].startswith(
        "application/octet-stream"
    )
    assert "attachment" in response.headers.get(
        "content-disposition", ""
    )
    assert response.headers.get(
        "x-content-type-options"
    ) == "nosniff"
    assert "object_key" not in (
        response.headers
    )
