from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from app.artifact_delivery.errors import (
    ArtifactExportLimitExceeded,
    ArtifactPreviewUnsupported,
)
from app.artifact_delivery.service import (
    ArtifactDeliveryService,
    canonical_json_bytes,
)
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.storage.errors import ArtifactIntegrityError
from app.storage.ports import OpenedArtifact, OpenedBlob
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


class TrackingBytesIO(io.BytesIO):
    was_closed = False

    def close(self) -> None:
        self.was_closed = True
        super().close()


def make_view(
    artifact_id: str,
    relative_path: str,
    media_type: str,
    content: bytes,
) -> ArtifactView:
    return ArtifactView(
        artifact_id=artifact_id,
        run_id="run-1",
        layer=relative_path.split("/", 1)[0],
        relative_path=relative_path,
        media_type=media_type,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        producer_node="test",
        created_at="2026-08-06T00:00:00+00:00",
    )


class FakeCatalog:
    def __init__(self, items: list[tuple[ArtifactView, bytes]]) -> None:
        self.items = {
            view.artifact_id: (view, content)
            for view, content in items
        }
        self.last_body: TrackingBytesIO | None = None

    def list_views(self, _job: JobRecord) -> list[ArtifactView]:
        return [view for view, _content in self.items.values()]

    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        view, content = self.items[artifact_id]
        descriptor = ArtifactDescriptor(
            artifact_id=view.artifact_id,
            run_id=view.run_id,
            layer=view.layer,
            relative_path=view.relative_path,
            media_type=view.media_type,
            sha256=view.sha256,
            size_bytes=view.size_bytes,
            producer_node=view.producer_node,
            created_at=view.created_at,
        )
        body = TrackingBytesIO(content)
        self.last_body = body
        return OpenedArtifact(
            artifact=PublishedArtifact(
                job_id=job.job_id,
                descriptor=descriptor,
                backend="memory",
                object_key=f"objects/{artifact_id}",
                revision=1,
                published_at=view.created_at,
            ),
            blob=OpenedBlob(
                stat=BlobStat(
                    backend="memory",
                    object_key=f"objects/{artifact_id}",
                    size_bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                ),
                body=body,
            ),
        )


def fake_job() -> JobRecord:
    # Service 测试只需要公开身份；真实 JobRecord 构造由 API 测试覆盖。
    return cast(
        JobRecord,
        SimpleNamespace(job_id="job-1", run_id="run-1"),
    )


def make_service(
    tmp_path: Path,
    catalog: FakeCatalog,
    *,
    preview_max_bytes: int = 8,
    max_artifacts: int = 20,
    max_uncompressed: int = 1024 * 1024,
) -> ArtifactDeliveryService:
    return ArtifactDeliveryService(
        catalog=catalog,
        preview_max_bytes=preview_max_bytes,
        stream_chunk_bytes=4,
        export_allowed_root=tmp_path,
        export_staging_root=tmp_path / "exports/.staging",
        export_max_artifacts=max_artifacts,
        export_max_uncompressed_bytes=max_uncompressed,
        export_max_archive_bytes=1024 * 1024,
        export_staging_ttl_seconds=3600,
    )


def test_preview_is_bounded_utf8_and_closes_body(tmp_path: Path) -> None:
    content = "你好，artifact preview".encode()
    view = make_view(
        "a1",
        "reports/final.md",
        "text/markdown",
        content,
    )
    catalog = FakeCatalog([(view, content)])

    result = make_service(
        tmp_path,
        catalog,
        preview_max_bytes=8,
    ).preview(job=fake_job(), artifact_id="a1")

    assert result.truncated is True
    # 第 7～9 字节是全角逗号；上限 8 落在字符中间，安全退回 6 字节。
    assert result.returned_bytes == 6
    assert result.content == "你好"
    assert catalog.last_body is not None
    assert catalog.last_body.was_closed is True


@pytest.mark.parametrize(
    ("path", "media_type", "content"),
    [
        ("reports/page.html", "text/html", b"<script>x</script>"),
        ("reports/fake.txt", "text/plain", b"a\x00b"),
        ("reports/fake.txt", "text/plain", b"\xff\xfe"),
    ],
)
def test_preview_rejects_unsafe_or_non_text_content(
    tmp_path: Path,
    path: str,
    media_type: str,
    content: bytes,
) -> None:
    view = make_view("a1", path, media_type, content)
    catalog = FakeCatalog([(view, content)])

    with pytest.raises(ArtifactPreviewUnsupported):
        make_service(tmp_path, catalog).preview(
            job=fake_job(),
            artifact_id="a1",
        )

    assert catalog.last_body is not None
    assert catalog.last_body.was_closed is True


def test_export_contains_artifacts_and_verifiable_manifest(
    tmp_path: Path,
) -> None:
    first = b"# final\n"
    second = b'{"status":"succeeded"}'
    views = [
        make_view("a1", "reports/final.md", "text/markdown", first),
        make_view("a2", "reports/run.json", "application/json", second),
    ]
    catalog = FakeCatalog([(views[0], first), (views[1], second)])
    service = make_service(tmp_path, catalog)

    prepared = service.build_export(
        job=fake_job(),
        public_job={"job_id": "job-1", "status": "succeeded"},
    )

    assert prepared.path.is_file()
    with zipfile.ZipFile(prepared.path) as archive:
        assert archive.read("artifacts/reports/final.md") == first
        assert archive.read("artifacts/reports/run.json") == second
        assert json.loads(archive.read("metadata/job.json")) == {
            "job_id": "job-1",
            "status": "succeeded",
        }
        manifest = json.loads(
            archive.read("metadata/export_manifest.json")
        )

    expected_hash = manifest.pop("manifest_sha256")
    assert hashlib.sha256(
        canonical_json_bytes(manifest)
    ).hexdigest() == expected_hash
    assert prepared.sha256 == hashlib.sha256(
        prepared.path.read_bytes()
    ).hexdigest()
    prepared.path.unlink()


def test_export_rejects_snapshot_drift_and_removes_partial_zip(
    tmp_path: Path,
) -> None:
    content = b"original"
    view = make_view("a1", "reports/final.md", "text/markdown", content)

    class DriftingCatalog(FakeCatalog):
        def open(self, *, job: JobRecord, artifact_id: str) -> OpenedArtifact:
            opened = super().open(job=job, artifact_id=artifact_id)
            changed = opened.artifact.descriptor.model_copy(
                update={"relative_path": "reports/changed.md"}
            )
            return OpenedArtifact(
                artifact=opened.artifact.model_copy(
                    update={"descriptor": changed}
                ),
                blob=opened.blob,
            )

    service = make_service(
        tmp_path,
        DriftingCatalog([(view, content)]),
    )

    with pytest.raises(ArtifactIntegrityError):
        service.build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )

    staging = tmp_path / "exports/.staging"
    assert list(staging.glob("*.part")) == []
    assert list(staging.glob("*.zip")) == []


def test_export_rejects_duplicate_archive_paths(tmp_path: Path) -> None:
    first = make_view("a1", "reports/final.md", "text/markdown", b"one")
    # 大小写不同在 Linux 可并存，但在部分解压目标会冲突，也要拒绝。
    second = make_view("a2", "reports/FINAL.md", "text/markdown", b"two")
    catalog = FakeCatalog([(first, b"one"), (second, b"two")])

    with pytest.raises(ArtifactIntegrityError):
        make_service(tmp_path, catalog).build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )


def test_export_enforces_count_and_uncompressed_limits(tmp_path: Path) -> None:
    content = b"12345"
    view = make_view("a1", "reports/final.txt", "text/plain", content)
    catalog = FakeCatalog([(view, content)])

    with pytest.raises(ArtifactExportLimitExceeded):
        make_service(
            tmp_path,
            catalog,
            max_artifacts=20,
            max_uncompressed=4,
        ).build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )


def test_export_staging_cannot_escape_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    catalog = FakeCatalog([])
    service = ArtifactDeliveryService(
        catalog=catalog,
        preview_max_bytes=8,
        stream_chunk_bytes=4,
        export_allowed_root=allowed,
        export_staging_root=tmp_path / "outside",
        export_max_artifacts=20,
        export_max_uncompressed_bytes=1024,
        export_max_archive_bytes=1024,
        export_staging_ttl_seconds=3600,
    )

    with pytest.raises(ArtifactIntegrityError):
        service.build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )
