from __future__ import annotations

import os
import sys
import threading
import time

from app.config import settings
from app.execution.cancellation import (
    list_runtime_records,
    request_run_cancellation,
)
from app.execution.process_supervisor import (
    ProcessSupervisor,
    SupervisedExecutionRequest,
)
from app.schemas import ResourceBudget


def test_external_cancel_request_stops_supervisor(
    tmp_path,
    monkeypatch,
) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    workspace = tmp_path / "workspace"
    run_dir.mkdir(parents=True)
    workspace.mkdir()
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    request = SupervisedExecutionRequest(
        execution_id="exec_cancel",
        host_command=[
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
        ],
        cwd=workspace,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(run_dir / "home"),
        },
        run_dir=run_dir,
        action_id="action-1",
        stage="test_cancel",
        profile_id="test-local",
        backend="local",
        budget=ResourceBudget(
            max_wall_time_seconds=30,
            max_processes=4,
            max_log_bytes_per_stream=4096,
            max_preview_bytes=1024,
            sample_interval_seconds=0.05,
            terminate_grace_seconds=0.2,
        ),
    )
    holder = {}

    def run() -> None:
        holder["result"] = ProcessSupervisor().execute(request)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        active = [
            item
            for item in list_runtime_records(run_dir)
            if item.get("status") == "running"
        ]
        if active:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Supervisor did not become running")

    cancellation = request_run_cancellation(
        run_dir=run_dir,
        reason="test cancellation",
        requested_by="pytest",
    )
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert cancellation.execution_id == "exec_cancel"
    result = holder["result"]
    assert result.end_reason == "cancelled"
    assert result.cancelled is True
    assert result.cancellation_reason == "test cancellation"
