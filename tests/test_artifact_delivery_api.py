from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.artifact_delivery.service import ArtifactDeliveryService
from app.config import settings
from app.job_runtime.schemas import JobRequest
from app.job_runtime.service import JobService
from app.job_runtime.store import SqliteJobStore
from app.storage.artifact_repository import SqliteArtifactRepository
from app.storage.catalog import BlobStoreRegistry, PublishedArtifactCatalog
from app.storage.local_blob_store import LocalBlobStore
from app.storage.publisher import ArtifactPublisher
from app.tools.artifact_tools import build_artifact_record
from tests.workspace_helpers import (
    FakeWorkspaceSnapshotter,
    setup_local_execution_profile,
)


def test_artifact_preview_download_and_job_export(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")
    setup_local_execution_profile(tmp_path, monkeypatch)

    job_service = JobService(
        SqliteJobStore(tmp_path / "jobs.sqlite"),
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    job, _created = job_service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id=settings.default_execution_profile,
        ),
        thread_id="artifact-delivery-api",
        idempotency_key="artifact-delivery-api",
    )

    run_root = Path(job.run_dir)
    report = run_root / "reports/final.md"
    binary = run_root / "reports/model.bin"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Final\n<script>not executed</script>\n",
        encoding="utf-8",
    )
    binary.write_bytes(b"\x00\x01\x02")

    report_record = build_artifact_record(
        state={"run_id": job.run_id, "run_dir": job.run_dir},
        path=report,
        producer_node="test",
        media_type="text/markdown",
    )
    binary_record = build_artifact_record(
        state={"run_id": job.run_id, "run_dir": job.run_dir},
        path=binary,
        producer_node="test",
        media_type="application/octet-stream",
    )

    repository = SqliteArtifactRepository(tmp_path / "artifacts.sqlite")
    blob_store = LocalBlobStore(tmp_path / "blob-store")
    ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    ).publish(
        job=job,
        records=[report_record, binary_record],
    )
    catalog = PublishedArtifactCatalog(
        repository=repository,
        registry=BlobStoreRegistry([blob_store]),
    )

    # 删除原始文件，后续成功只能来自发布后的 BlobStore。
    report.unlink()
    binary.unlink()

    staging_root = tmp_path / "exports/.staging"
    delivery = ArtifactDeliveryService(
        catalog=catalog,
        preview_max_bytes=1024,
        stream_chunk_bytes=4,
        export_allowed_root=tmp_path,
        export_staging_root=staging_root,
        export_max_artifacts=10,
        export_max_uncompressed_bytes=1024 * 1024,
        export_max_archive_bytes=1024 * 1024,
        export_staging_ttl_seconds=3600,
    )
    app = create_api_app(
        job_service=job_service,
        artifact_catalog=catalog,
        artifact_delivery_service=delivery,
        api_token="test-token",
    )
    auth = {"Authorization": "Bearer test-token"}

    with TestClient(app) as client:
        unauthorized = client.get(
            f"/v1/jobs/{job.job_id}/artifacts"
        )
        assert unauthorized.status_code == 401

        listing = client.get(
            f"/v1/jobs/{job.job_id}/artifacts",
            headers=auth,
        )
        assert listing.status_code == 200
        items = {
            item["artifact_id"]: item
            for item in listing.json()["items"]
        }
        assert items[report_record.artifact_id]["preview_supported"] is True
        assert items[binary_record.artifact_id]["preview_supported"] is False
        assert "object_key" not in listing.text

        preview = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{report_record.artifact_id}/preview",
            headers=auth,
        )
        assert preview.status_code == 200
        assert "<script>not executed</script>" in preview.json()["content"]
        assert preview.json()["truncated"] is False

        rejected = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{binary_record.artifact_id}/preview",
            headers=auth,
        )
        assert rejected.status_code == 415
        assert rejected.json()["code"] == "ARTIFACT_PREVIEW_UNSUPPORTED"

        download = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{report_record.artifact_id}/download",
            headers=auth,
        )
        assert download.status_code == 200
        assert download.content.startswith(b"# Final")
        assert download.headers["content-type"].startswith(
            "application/octet-stream"
        )
        assert "attachment" in download.headers["content-disposition"]
        assert download.headers["x-artifact-sha256"] == report_record.sha256
        assert download.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in download.headers["content-security-policy"]

        # 旧 Chat citation 使用的 /content 仍然有效，并走同一安全响应。
        compatibility = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{report_record.artifact_id}/content",
            headers=auth,
        )
        assert compatibility.status_code == 200
        assert compatibility.content == download.content

        exported = client.get(
            f"/v1/jobs/{job.job_id}/export",
            headers=auth,
        )
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("application/zip")
        assert "attachment" in exported.headers["content-disposition"]
        assert len(exported.headers["x-export-sha256"]) == 64

    # TestClient 已消费完整响应，generator finally 应删除临时 ZIP。
    assert list(staging_root.glob("*.part")) == []
    assert list(staging_root.glob("*.zip")) == []

    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert archive.read("artifacts/reports/final.md").startswith(b"# Final")
        assert archive.read("artifacts/reports/model.bin") == b"\x00\x01\x02"
        manifest = json.loads(
            archive.read("metadata/export_manifest.json")
        )
        public_job = json.loads(archive.read("metadata/job.json"))

    assert manifest["job_id"] == job.job_id
    assert manifest["run_id"] == job.run_id
    assert manifest["artifact_count"] == 2
    serialized = json.dumps(
        {"manifest": manifest, "job": public_job},
        ensure_ascii=False,
    )
    assert "run_dir" not in serialized
    assert "object_key" not in serialized
    assert "claim_token" not in serialized
