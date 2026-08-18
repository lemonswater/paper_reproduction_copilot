from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from app.chat.context import ChatContextBuilder
from app.interaction.schemas import (
    ArtifactView,
    LogTailResponse,
)
from app.storage.ports import OpenedArtifact, OpenedBlob
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)
from tests.helpers.interaction import make_job


class FakeInteraction:
    def __init__(self):
        self.internal_job = SimpleNamespace(
            job_id="job-1"
        )
        self.job_service = SimpleNamespace(
            get=self._get_internal_job
        )

    def _get_internal_job(self, job_id: str):
        assert job_id == "job-1"
        return self.internal_job

    def get_job(self, job_id: str):
        assert job_id == "job-1"
        return make_job()

    def events_after(self, **_kwargs):
        return []

    def tail_log(self, **_kwargs):
        return LogTailResponse(lines=100)


class FakeCatalog:
    def __init__(self):
        self.body = BytesIO(
            b"final metric is 91.2 according to the report"
        )
        self.opened_ids: list[str] = []

    def list_views(self, job):
        assert job.job_id == "job-1"
        return [
            ArtifactView(
                artifact_id="report-1",
                run_id="run-1",
                layer="reports",
                relative_path="reports/final_report.md",
                media_type="text/markdown",
                sha256="a" * 64,
                size_bytes=48,
                producer_node="final_report",
                created_at="2026-08-01T00:00:00Z",
            ),
            ArtifactView(
                artifact_id="patch-1",
                run_id="run-1",
                layer="patches",
                relative_path="patches/change.diff",
                media_type="text/plain",
                sha256="b" * 64,
                size_bytes=10,
                producer_node="patch_builder",
                created_at="2026-08-01T00:00:00Z",
            ),
        ]

    def open(self, *, job, artifact_id: str):
        assert job.job_id == "job-1"
        assert artifact_id == "report-1"
        self.opened_ids.append(artifact_id)
        descriptor = ArtifactDescriptor(
            artifact_id="report-1",
            run_id="run-1",
            layer="reports",
            relative_path="reports/final_report.md",
            media_type="text/markdown",
            sha256="a" * 64,
            size_bytes=48,
            producer_node="final_report",
            created_at="2026-08-01T00:00:00Z",
        )
        return OpenedArtifact(
            artifact=PublishedArtifact(
                job_id="job-1",
                descriptor=descriptor,
                backend="fake",
                object_key="not-public",
                revision=1,
                published_at="2026-08-01T00:00:00Z",
            ),
            blob=OpenedBlob(
                stat=BlobStat(
                    backend="fake",
                    object_key="not-public",
                    size_bytes=48,
                    sha256="a" * 64,
                ),
                body=self.body,
            ),
        )


def test_context_uses_allowed_artifact_and_closes_body():
    interaction = FakeInteraction()
    catalog = FakeCatalog()
    builder = ChatContextBuilder(
        interaction=interaction,
        artifact_catalog=catalog,
        artifacts_to_open=5,
        source_limit=4,
        artifact_max_bytes=4096,
        total_context_chars=10000,
        log_max_bytes=4096,
    )

    bundle = builder.build(
        job_id="job-1",
        question="What is the final metric?",
    )

    assert catalog.opened_ids == ["report-1"]
    assert catalog.body.closed
    encoded = "\n".join(
        item.content for item in bundle.sources
    )
    assert "91.2" in encoded
    assert all(
        item.citation.artifact_id != "patch-1"
        for item in bundle.sources
    )
