from __future__ import annotations

import json

from typer.testing import CliRunner

from app.config import settings
from app.job_runtime.factory import (
    build_job_store,
)
from app.job_runtime.schemas import (
    JobInterrupt,
    JobRequest,
)
from app.job_runtime.service import (
    JobService,
    build_job_service,
)
from app.main import app
from tests.workspace_helpers import (
    FakeWorkspaceSnapshotter,
    setup_local_execution_profile,
    worker_fixture,
)


def _build_test_service() -> JobService:
    """JobService with FakeWorkspaceSnapshotter for CLI tests."""

    return JobService(
        build_job_store(),
        workspace_snapshotter=(
            FakeWorkspaceSnapshotter()
        ),
    )


def _configure_runtime(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "job_db_path",
        tmp_path / "jobs/runtime.sqlite",
    )
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    policy_hash = setup_local_execution_profile(
        tmp_path, monkeypatch
    )
    # CLI 命令内部调用 build_job_service()，用 fake snapshotter 避免读真实文件。
    monkeypatch.setattr(
        "app.main.build_job_service",
        _build_test_service,
    )
    return policy_hash


def test_submit_and_show_job_cli(
    tmp_path,
    monkeypatch,
) -> None:
    _configure_runtime(
        tmp_path,
        monkeypatch,
    )
    runner = CliRunner()

    submitted = runner.invoke(
        app,
        [
            "submit-job",
            "/data/paper.pdf",
            "/data/repo",
            "--thread-id",
            "cli-job-thread",
            "--idempotency-key",
            "cli-submit-1",
        ],
    )
    assert submitted.exit_code == 0
    assert "job_id" in submitted.stdout
    assert "queued" in submitted.stdout

    record = build_job_service().list()[0]
    shown = runner.invoke(
        app,
        ["show-job", record.job_id],
    )
    assert shown.exit_code == 0
    assert "cli-job-thread" in shown.stdout
    assert record.run_id in shown.stdout


def test_cancel_queued_job_cli(
    tmp_path,
    monkeypatch,
) -> None:
    _configure_runtime(
        tmp_path,
        monkeypatch,
    )
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "submit-job",
            "/data/paper.pdf",
            "/data/repo",
            "--thread-id",
            "cancel-thread",
        ],
    )
    record = build_job_service().list()[0]

    cancelled = runner.invoke(
        app,
        [
            "cancel-job",
            record.job_id,
            "--reason",
            "cli test stop",
        ],
    )

    assert cancelled.exit_code == 0
    assert "cancelled" in cancelled.stdout
    assert (
        build_job_service()
        .get(record.job_id)
        .status
        == "cancelled"
    )


def test_resume_job_cli_reads_json_input(
    tmp_path,
    monkeypatch,
) -> None:
    policy_hash = _configure_runtime(
        tmp_path,
        monkeypatch,
    )
    service = _build_test_service()
    record, _ = service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id=(
                settings.default_execution_profile
            ),
        ),
        thread_id="resume-thread",
    )
    service.store.register_worker(
        worker=worker_fixture(
            worker_id="test-worker",
            policy_hash=policy_hash,
        ),
        lease_seconds=30,
    )
    claim = service.store.claim_next(
        worker=worker_fixture(
            worker_id="test-worker",
            policy_hash=policy_hash,
        ),
        lease_seconds=30,
    )
    assert claim is not None
    service.store.mark_waiting(
        job_id=record.job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="command_selection",
                value_preview={},
            )
        ],
        result={},
        actor="test-worker",
    )

    input_path = (
        tmp_path
        / "command_selection_input.json"
    )
    input_path.write_text(
        json.dumps(
            {
                "run_commands_hash": "abc",
                "selected_index": 0,
                "edits": [],
            }
        ),
        encoding="utf-8",
    )

    resumed = CliRunner().invoke(
        app,
        [
            "resume-job",
            record.job_id,
            "--expected-node",
            "command_selection",
            "--input",
            str(input_path),
        ],
    )

    assert resumed.exit_code == 0
    current = service.get(record.job_id)
    assert current.status == "queued"
    assert current.pending_resume_id is not None