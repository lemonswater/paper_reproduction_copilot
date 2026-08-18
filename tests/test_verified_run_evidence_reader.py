# tests/test_verified_run_evidence_reader.py
from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace

import pytest

from app.interaction.schemas import ArtifactView
from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
)
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.workspace.repository import workspace_manifest_hash
from app.workspace.schemas import (
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _workspace(
    *,
    job_id: str = "job-parent",
    run_id: str = "run-parent",
) -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_id=f"manifest-{job_id}",
        manifest_hash="0" * 64,
        job_id=job_id,
        run_id=run_id,
        generation=2,
        source_host_id="host-a",
        entries=[
            WorkspaceBlobEntry(
                logical_path="inputs/paper.pdf",
                role="paper",
                object_key=f"workspace/{job_id}/paper.pdf",
                sha256="a" * 64,
                size_bytes=128,
                media_type="application/pdf",
            ),
            WorkspaceBlobEntry(
                logical_path="inputs/repository.bundle",
                role="repository_bundle",
                object_key=f"workspace/{job_id}/repository.bundle",
                sha256="b" * 64,
                size_bytes=256,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="c" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="inputs/repository.bundle",
        ),
        portable=True,
        created_at="2026-08-09T00:00:00+00:00",
    )
    return draft.model_copy(
        update={"manifest_hash": workspace_manifest_hash(draft)}
    )


def _job(manifest: WorkspaceManifest, *, status: str = "succeeded"):
    return SimpleNamespace(
        job_id=manifest.job_id,
        run_id=manifest.run_id,
        status=status,
        version=4,
        updated_at="2026-08-09T00:10:00+00:00",
        workspace_manifest_id=manifest.manifest_id,
        workspace_manifest_generation=manifest.generation,
    )


def _run_manifest(*, job_id: str, run_id: str) -> bytes:
    payload = {
        "manifest_version": 4,
        "job_id": job_id,
        "run_id": run_id,
        "experiment_goal": "test",
        "final_status": "succeeded",
        "execution_profile": {"profile_id": "cpu-local", "fingerprint": "d" * 64},
        "execution_supervision": {
            "end_reason": "exited",
            "resource_usage": {
                "peak_rss_bytes": 1024,
                "total_cpu_seconds": 1.0,
                "peak_process_count": 1,
                "total_write_bytes": 0,
            },
        },
        "selected_run_command": {
            "command": "python train.py --epochs 50",
            "cwd": "/data/repo",
            "source": "readme",
            "risk_level": "low",
        },
        "execution": {"result": {"ok": True, "returncode": 0}},
        "errors": {"items": []},
        "smoke_test": {"status": "passed", "passed": True},
        "repair": {"attempt_count": 0},
        "file_repair": {"attempt_count": 0},
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class FakeJobs:
    def __init__(self):
        self.jobs: dict[str, object] = {}
        self.manifests: dict[str, WorkspaceManifest] = {}

    def add(self, job, manifest: WorkspaceManifest) -> None:
        self.jobs[job.job_id] = job
        self.manifests[manifest.manifest_id] = manifest

    def get(self, job_id: str):
        return self.jobs[job_id]

    def get_workspace_manifest(self, manifest_id: str) -> WorkspaceManifest:
        return self.manifests[manifest_id]


class FakeCatalog:
    def __init__(self):
        self.views: dict[str, list[ArtifactView]] = {}
        self.payloads: dict[tuple[str, str], bytes] = {}

    def add_run(self, *, job, manifest_bytes: bytes) -> None:
        manifest_view = ArtifactView(
            artifact_id=f"artifact-manifest-{job.job_id}",
            run_id=job.run_id,
            layer="reports",
            relative_path="reports/run_manifest.json",
            media_type="application/json",
            sha256=_sha(manifest_bytes),
            size_bytes=len(manifest_bytes),
            producer_node="run_manifest",
            created_at="2026-08-09T00:11:00+00:00",
        )
        self.views[job.job_id] = [manifest_view]
        self.payloads[(job.job_id, manifest_view.artifact_id)] = manifest_bytes

    def corrupt_blob(self, job_id: str) -> None:
        """Append extra bytes to break SHA-256."""
        for key in list(self.payloads):
            if key[0] == job_id:
                self.payloads[key] += b"tampered"

    def duplicate_run_manifest(self, job_id: str) -> None:
        """Add a second run_manifest.json to create ambiguity."""
        views = self.views[job_id]
        original = views[0]
        dup = original.model_copy(
            update={
                "artifact_id": f"artifact-manifest-dup-{job_id}",
            }
        )
        views.append(dup)
        self.payloads[(job_id, dup.artifact_id)] = self.payloads[
            (job_id, original.artifact_id)
        ]

    def list_views(self, job):
        return list(self.views[job.job_id])

    def open(self, *, job, artifact_id: str):
        view = next(
            item
            for item in self.views[job.job_id]
            if item.artifact_id == artifact_id
        )
        raw = self.payloads[(job.job_id, artifact_id)]
        descriptor = SimpleNamespace(
            artifact_id=view.artifact_id,
            relative_path=view.relative_path,
            run_id=view.run_id,
            sha256=view.sha256,
            size_bytes=view.size_bytes,
        )
        stat = SimpleNamespace(
            sha256=view.sha256,
            size_bytes=view.size_bytes,
        )
        return SimpleNamespace(
            artifact=SimpleNamespace(descriptor=descriptor),
            blob=SimpleNamespace(stat=stat, body=io.BytesIO(raw)),
        )


@pytest.fixture
def fixture():
    jobs = FakeJobs()
    catalog = FakeCatalog()
    workspace = _workspace()
    job = _job(workspace, status="succeeded")
    jobs.add(job, workspace)
    manifest_bytes = _run_manifest(
        job_id=job.job_id, run_id=job.run_id
    )
    catalog.add_run(job=job, manifest_bytes=manifest_bytes)

    reader = VerifiedRunEvidenceReader(
        jobs=jobs,
        artifact_catalog=catalog,
        max_manifest_bytes=1024 * 1024,
        max_artifacts=100,
    )
    return SimpleNamespace(
        reader=reader,
        job=job,
        workspace=workspace,
        catalog=catalog,
        jobs=jobs,
    )


def test_reader_returns_verified_terminal_evidence(fixture):
    evidence = fixture.reader.read(fixture.job.job_id)
    assert evidence.job.job_id == fixture.job.job_id
    assert evidence.workspace.manifest_id == fixture.workspace.manifest_id
    assert evidence.run_manifest["run_id"] == fixture.job.run_id


def test_reader_rejects_non_terminal_job(fixture):
    fixture.job.status = "running"
    with pytest.raises(RunEvidenceConflictError):
        fixture.reader.read(fixture.job.job_id)


def test_reader_rejects_catalog_blob_sha_mismatch(fixture):
    fixture.catalog.corrupt_blob(fixture.job.job_id)
    with pytest.raises(RunEvidenceIntegrityError):
        fixture.reader.read(fixture.job.job_id)


def test_reader_rejects_workspace_hash_mismatch(fixture):
    fixture.workspace.manifest_hash = "0" * 64
    with pytest.raises(RunEvidenceIntegrityError):
        fixture.reader.read(fixture.job.job_id)


def test_reader_rejects_duplicate_run_manifest(fixture):
    fixture.catalog.duplicate_run_manifest(fixture.job.job_id)
    with pytest.raises(RunEvidenceIntegrityError):
        fixture.reader.read(fixture.job.job_id)
