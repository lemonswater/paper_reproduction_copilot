from __future__ import annotations

import json

from typer.testing import CliRunner

from app.config import settings
from app.execution.cancellation import write_runtime_record
from app.main import app


def _prepare_active_run(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-control"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "runs_dir", runs_dir)
    write_runtime_record(
        run_dir=run_dir,
        execution_id="exec_control",
        payload={
            "execution_id": "exec_control",
            "status": "running",
            "pid": 12345,
            "pgid": 12345,
        },
    )
    return run_dir


def test_show_process_lists_supervised_execution(
    tmp_path,
    monkeypatch,
) -> None:
    run_dir = _prepare_active_run(tmp_path, monkeypatch)

    result = CliRunner().invoke(
        app,
        ["show-process", "--run-id", run_dir.name],
    )

    assert result.exit_code == 0
    assert "exec_control" in result.stdout
    assert "running" in result.stdout


def test_cancel_run_writes_request_for_only_active_execution(
    tmp_path,
    monkeypatch,
) -> None:
    run_dir = _prepare_active_run(tmp_path, monkeypatch)

    result = CliRunner().invoke(
        app,
        [
            "cancel-run",
            "--run-id",
            run_dir.name,
            "--reason",
            "operator stop",
        ],
    )

    assert result.exit_code == 0
    request_path = (
        run_dir
        / "execution"
        / "control"
        / "exec_control.cancel.json"
    )
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    assert payload["execution_id"] == "exec_control"
    assert payload["reason"] == "operator stop"
    assert payload["requested_by"] == "cli"


def test_process_control_requires_exactly_one_run_selector() -> None:
    result = CliRunner().invoke(app, ["show-process"])

    assert result.exit_code == 2
    assert "必须且只能提供" in result.stderr
