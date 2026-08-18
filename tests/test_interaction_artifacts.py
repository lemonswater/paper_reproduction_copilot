from __future__ import annotations

import pytest

from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.job_runtime.errors import (
    JobConflictError,
)
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.tools.artifact_tools import (
    build_artifact_record,
)
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
)


def _job_and_state(
    tmp_path,
    monkeypatch,
):
    runs_root = tmp_path / "runs"
    monkeypatch.setattr(
        settings,
        "runs_dir",
        runs_root,
    )
    run_root = runs_root / "run-artifact"
    target = (
        run_root
        / "reports"
        / "final_report.md"
    )
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    target.write_text(
        "report",
        encoding="utf-8",
    )

    state = {
        "run_id": "run-artifact",
        "run_dir": str(run_root),
    }
    record = build_artifact_record(
        state=state,
        path=target,
        producer_node="test",
    )
    state["artifact_records"] = [
        record.model_dump()
    ]

    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    job, _ = store.submit(
        job_id="job-artifact",
        idempotency_key="submit-artifact",
        thread_id="thread-artifact",
        run_id="run-artifact",
        run_dir=str(run_root),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(
            suffix="artifact"
        ),
        max_attempts=3,
    )
    return job, state, record, target


def test_catalog_does_not_expose_absolute_path(
    tmp_path,
    monkeypatch,
):
    job, state, record, _ = (
        _job_and_state(
            tmp_path,
            monkeypatch,
        )
    )
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: state
    )

    dumped = (
        catalog.list_views(job)[0]
        .model_dump()
    )

    assert dumped["artifact_id"] == (
        record.artifact_id
    )
    assert "absolute_path" not in dumped


def test_download_rechecks_hash(
    tmp_path,
    monkeypatch,
):
    job, state, record, target = (
        _job_and_state(
            tmp_path,
            monkeypatch,
        )
    )
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: state
    )
    target.write_text(
        "tampered",
        encoding="utf-8",
    )

    with pytest.raises(
        JobConflictError,
        match="SHA-256|大小",
    ):
        catalog.resolve(
            job=job,
            artifact_id=(
                record.artifact_id
            ),
        )


def test_symlink_escape_is_rejected(
    tmp_path,
    monkeypatch,
):
    job, state, record, target = (
        _job_and_state(
            tmp_path,
            monkeypatch,
        )
    )
    outside = tmp_path / "outside.txt"
    outside.write_text(
        "outside",
        encoding="utf-8",
    )
    target.unlink()
    target.symlink_to(outside)
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: state
    )

    with pytest.raises(
        JobConflictError,
        match="逃逸",
    ):
        catalog.resolve(
            job=job,
            artifact_id=(
                record.artifact_id
            ),
        )