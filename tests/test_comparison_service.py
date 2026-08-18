from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace

import pytest

from app.comparison.errors import (
    ComparisonConflictError,
    ComparisonIntegrityError,
)
from app.comparison.repository import FileComparisonRepository
from app.comparison.schemas import ComparisonCreateRequest
from app.comparison.service import ComparisonService, build_command_snapshot
from app.interaction.schemas import ArtifactView
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
    job_id: str,
    run_id: str,
    paper_sha256: str = "a" * 64,
    commit: str = "b" * 40,
) -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_id=f"manifest-{job_id}",
        manifest_hash="0" * 64,
        job_id=job_id,
        run_id=run_id,
        generation=0,
        source_host_id="test-host",
        entries=[
            WorkspaceBlobEntry(
                logical_path="inputs/paper.pdf",
                role="paper",
                object_key=f"workspace/{job_id}/paper.pdf",
                sha256=paper_sha256,
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
            commit_sha=commit,
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


def _job(
    manifest: WorkspaceManifest,
    *,
    status: str,
):
    return SimpleNamespace(
        job_id=manifest.job_id,
        run_id=manifest.run_id,
        status=status,
        version=4,
        updated_at="2026-08-09T00:10:00+00:00",
        workspace_manifest_id=manifest.manifest_id,
        workspace_manifest_generation=manifest.generation,
        request=SimpleNamespace(
            experiment_goal="复现论文 main result",
        ),
        requirements=SimpleNamespace(
            execution_profile_id="cpu-local",
            execution_policy_hash="c" * 64,
            execution_backend="local",
        ),
    )


def _run_manifest(
    *,
    job_id: str,
    run_id: str,
    command: str,
    final_status: str,
    ok: bool,
    returncode: int,
    errors: list[dict] | None = None,
) -> bytes:
    payload = {
        "manifest_version": 4,
        "job_id": job_id,
        "run_id": run_id,
        "experiment_goal": "复现论文 main result",
        "final_status": final_status,
        "execution_profile": {
            "profile_id": "cpu-local",
            "fingerprint": "d" * 64,
        },
        "execution_supervision": {
            "end_reason": "exited",
            "resource_usage": {
                "peak_rss_bytes": 1024,
                "total_cpu_seconds": 1.5,
                "peak_process_count": 2,
                "total_write_bytes": 64,
            },
        },
        "selected_run_command": {
            "command": command,
            "cwd": "/data/private/repository",
            "source": "readme",
            "risk_level": "low",
        },
        "execution": {
            "result": {
                "ok": ok,
                "returncode": returncode,
            }
        },
        "errors": {
            "items": errors or [],
        },
        "smoke_test": {
            "status": "passed" if ok else "blocked",
            "passed": ok,
        },
        "repair": {"attempt_count": 0},
        "file_repair": {"attempt_count": 0},
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class FakeJobs:
    def __init__(self):
        self.jobs = {}
        self.manifests = {}

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

    def add_run(
        self,
        *,
        job,
        manifest_bytes: bytes,
        output_sha: str,
    ) -> None:
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
        output_view = ArtifactView(
            artifact_id=f"artifact-output-{job.job_id}",
            run_id=job.run_id,
            layer="execution",
            relative_path="execution/metrics.json",
            media_type="application/json",
            sha256=output_sha,
            size_bytes=20,
            producer_node="executor",
            created_at="2026-08-09T00:11:00+00:00",
        )
        self.views[job.job_id] = [manifest_view, output_view]
        self.payloads[(job.job_id, manifest_view.artifact_id)] = manifest_bytes

    def list_views(self, job):
        return list(self.views[job.job_id])

    def open(self, *, job, artifact_id: str):
        view = next(
            item for item in self.views[job.job_id] if item.artifact_id == artifact_id
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


def _service(tmp_path):
    jobs = FakeJobs()
    catalog = FakeCatalog()

    base_workspace = _workspace(job_id="job-base", run_id="run-base")
    target_workspace = _workspace(job_id="job-target", run_id="run-target")
    base_job = _job(base_workspace, status="failed")
    target_job = _job(target_workspace, status="succeeded")
    jobs.add(base_job, base_workspace)
    jobs.add(target_job, target_workspace)

    base_bytes = _run_manifest(
        job_id=base_job.job_id,
        run_id=base_job.run_id,
        command="python train.py --dataset=/data/private/ntu --batch-size 8",
        final_status="failed",
        ok=False,
        returncode=1,
        errors=[
            {
                "code": "MODULE_NOT_FOUND",
                "category": "environment",
                "stage": "executor",
                "terminal": False,
                "message": "module missing at /data/private/repository/modules",
            }
        ],
    )
    target_bytes = _run_manifest(
        job_id=target_job.job_id,
        run_id=target_job.run_id,
        command="python train.py --dataset=/data/private/ntu --batch-size 16",
        final_status="succeeded",
        ok=True,
        returncode=0,
    )
    catalog.add_run(
        job=base_job,
        manifest_bytes=base_bytes,
        output_sha="e" * 64,
    )
    catalog.add_run(
        job=target_job,
        manifest_bytes=target_bytes,
        output_sha="f" * 64,
    )
    repository = FileComparisonRepository(
        tmp_path / "comparisons",
        max_report_bytes=1024 * 1024,
        list_scan_limit=100,
        staging_ttl_seconds=60,
    )
    reader = VerifiedRunEvidenceReader(
        jobs=jobs,
        artifact_catalog=catalog,
        max_manifest_bytes=1024 * 1024,
        max_artifacts=100,
    )
    return (
        ComparisonService(
            evidence_reader=reader,
            repository=repository,
            max_changes=100,
        ),
        jobs,
        catalog,
        base_bytes,
        target_bytes,
    )


def test_command_projection_redacts_secrets_and_absolute_paths() -> None:
    snapshot = build_command_snapshot(
        {
            "command": (
                "python /data/private/train.py "
                "--dataset=/data/private/ntu --token top-secret --batch-size 8"
            ),
            "cwd": "/data/private/repository",
        }
    )
    assert "/data/private" not in snapshot.display
    assert "top-secret" not in snapshot.display
    assert "--batch-size 8" in snapshot.display
    assert snapshot.command_sha256 is not None
    assert snapshot.cwd_sha256 is not None


def test_service_creates_verified_deterministic_diff(tmp_path) -> None:
    service, _jobs, catalog, base_before, target_before = _service(tmp_path)
    request = ComparisonCreateRequest(
        base_job_id="job-base",
        target_job_id="job-target",
    )

    first = service.create(request)
    second = service.create(request)

    assert first.comparison_id == second.comparison_id
    assert first.summary.high_count >= 3
    assert {item.category for item in first.changes} >= {
        "command",
        "execution",
        "error",
        "artifact",
    }
    rendered = first.model_dump_json()
    assert "/data/private" not in rendered
    assert "module missing at" not in rendered
    # Comparison 创建过程不能改写源 Artifact。
    assert catalog.payloads[("job-base", "artifact-manifest-job-base")] == base_before
    assert catalog.payloads[("job-target", "artifact-manifest-job-target")] == target_before


def test_service_rejects_cross_paper_by_default(tmp_path) -> None:
    service, jobs, _catalog, _base, _target = _service(tmp_path)
    target = jobs.manifests["manifest-job-target"]
    changed = _workspace(
        job_id="job-target",
        run_id="run-target",
        paper_sha256="9" * 64,
    )
    jobs.manifests[target.manifest_id] = changed

    with pytest.raises(ComparisonConflictError, match="paper SHA-256"):
        service.create(
            ComparisonCreateRequest(
                base_job_id="job-base",
                target_job_id="job-target",
            )
        )


def test_service_rejects_non_terminal_job(tmp_path) -> None:
    service, jobs, _catalog, _base, _target = _service(tmp_path)
    jobs.jobs["job-target"].status = "running"
    with pytest.raises(ComparisonConflictError, match="尚未终止"):
        service.create(
            ComparisonCreateRequest(
                base_job_id="job-base",
                target_job_id="job-target",
            )
        )


def test_service_detects_manifest_blob_tampering(tmp_path) -> None:
    service, _jobs, catalog, _base, _target = _service(tmp_path)
    key = ("job-target", "artifact-manifest-job-target")
    catalog.payloads[key] += b" "

    with pytest.raises(ComparisonIntegrityError):
        service.create(
            ComparisonCreateRequest(
                base_job_id="job-base",
                target_job_id="job-target",
            )
        )
