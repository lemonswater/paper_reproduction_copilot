from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace

import pytest

from app.failure_memory.errors import (
    FailureCaseConflictError,
    FailureCaseIntegrityError,
)
from app.failure_memory.evidence_reader import FailureEvidenceReader
from app.schemas import DebugReport
from tests.helpers.failure_memory import make_stage_error


class FakeVerifiedRuns:
    def __init__(self, evidence):
        self.evidence = evidence

    def read(self, job_id):
        assert job_id == self.evidence.job.job_id
        return self.evidence


class FakeArtifactCatalog:
    def __init__(self, *, views, blobs):
        self.views = {item.artifact_id: item for item in views}
        self.blobs = dict(blobs)

    def open(self, *, job, artifact_id):
        del job
        view = self.views[artifact_id]
        raw = self.blobs[artifact_id]
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
            blob=SimpleNamespace(
                stat=stat,
                body=io.BytesIO(raw),
            ),
        )


def _view(*, artifact_id, path, run_id, raw):
    return SimpleNamespace(
        artifact_id=artifact_id,
        relative_path=path,
        run_id=run_id,
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
    )


def _fixture(*, final_status="failed", include_log=True):
    job_id = "job-failed"
    run_id = "run-failed"
    error = make_stage_error()
    log_raw = (
        b'Traceback (most recent call last):\n'
        b'  File "/repo/modules/setup.py", line 42, in build_ext\n'
        b'RuntimeError: CUDA extension build failed\n'
    )
    debug_raw = json.dumps(
        DebugReport(
            error_type="cuda_extension_build",
            most_likely_causes=["GCC mismatch"],
            suggested_fixes=["Use a compatible profile"],
        ).model_dump(mode="json")
    ).encode("utf-8")
    error_raw = json.dumps(
        {"errors": [error.model_dump(mode="json")]}
    ).encode("utf-8")
    manifest = {
        "manifest_version": 5,
        "job_id": job_id,
        "run_id": run_id,
        "final_status": final_status,
        "execution_profile": {"fingerprint": "profile-source-v1"},
        "execution": {
            "log_path": "/untrusted/outside/combined.log",
            "evidence": {
                "artifact_ids": ["artifact-log"] if include_log else []
            },
            "verification": None,
        },
        "errors": {
            "items": (
                [error.model_dump(mode="json")]
                if final_status != "succeeded"
                else []
            )
        },
    }
    manifest_raw = json.dumps(manifest).encode("utf-8")
    manifest_view = _view(
        artifact_id="artifact-manifest",
        path="reports/run_manifest.json",
        run_id=run_id,
        raw=manifest_raw,
    )
    debug_view = _view(
        artifact_id="artifact-debug",
        path="debug/debug_report.json",
        run_id=run_id,
        raw=debug_raw,
    )
    error_view = _view(
        artifact_id="artifact-errors",
        path="reports/error_report.json",
        run_id=run_id,
        raw=error_raw,
    )
    log_view = _view(
        artifact_id="artifact-log",
        path="execution/attempt-1/combined.log",
        run_id=run_id,
        raw=log_raw,
    )
    views = [manifest_view, debug_view, error_view, log_view]
    evidence = SimpleNamespace(
        job=SimpleNamespace(
            job_id=job_id,
            run_id=run_id,
            version=3,
            request=SimpleNamespace(execution_profile_id="local"),
            requirements=SimpleNamespace(execution_backend="local"),
        ),
        workspace=SimpleNamespace(
            manifest_id="manifest-failed",
            manifest_hash="b" * 64,
            repository=SimpleNamespace(
                commit_sha="a" * 40,
                clean=True,
            ),
            source_paths=SimpleNamespace(repo_path="/repo"),
        ),
        artifacts=tuple(views),
        run_manifest_artifact=manifest_view,
        run_manifest=manifest,
    )
    catalog = FakeArtifactCatalog(
        views=views,
        blobs={
            "artifact-manifest": manifest_raw,
            "artifact-debug": debug_raw,
            "artifact-errors": error_raw,
            "artifact-log": log_raw,
        },
    )
    return evidence, catalog


def _reader(evidence, catalog, *, max_log_bytes=2 * 1024 * 1024):
    return FailureEvidenceReader(
        verified_runs=FakeVerifiedRuns(evidence),
        artifact_catalog=catalog,
        max_json_bytes=2 * 1024 * 1024,
        max_log_bytes=max_log_bytes,
    )


def test_reader_builds_snapshot_from_verified_failed_run():
    evidence, catalog = _fixture()
    snapshot = _reader(evidence, catalog).read("job-failed")
    assert snapshot.stage_error.terminal is True
    assert snapshot.source.run_manifest_sha256 == (
        evidence.run_manifest_artifact.sha256
    )
    assert snapshot.source.environment.repository_commit == "a" * 40
    assert "modules/setup.py" in snapshot.traceback_text
    assert any(
        item.purpose == "run_manifest"
        for item in snapshot.source.evidence
    )


def test_reader_rejects_success_without_failure_semantics():
    evidence, catalog = _fixture(final_status="succeeded")
    with pytest.raises(FailureCaseConflictError):
        _reader(evidence, catalog).read("job-failed")


def test_reader_rejects_tampered_debug_artifact():
    evidence, catalog = _fixture()
    catalog.blobs["artifact-debug"] += b"tampered"
    with pytest.raises(FailureCaseIntegrityError):
        _reader(evidence, catalog).read("job-failed")


def test_reader_does_not_follow_unpublished_log_path():
    evidence, catalog = _fixture(include_log=False)
    snapshot = _reader(evidence, catalog).read("job-failed")
    assert snapshot.traceback_text == ""


def test_oversized_log_is_not_copied_into_snapshot():
    evidence, catalog = _fixture()
    snapshot = _reader(
        evidence,
        catalog,
        max_log_bytes=16,
    ).read("job-failed")
    assert snapshot.traceback_text == ""
    assert not any(
        item.purpose == "process_log"
        for item in snapshot.source.evidence
    )
