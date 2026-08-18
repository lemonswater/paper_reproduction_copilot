from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import psutil

from app.config import settings
from app.execution.process_supervisor import (
    ProcessSupervisor,
    SupervisedExecutionRequest,
    budget_end_reason,
)
from app.schemas import ResourceBudget, ResourceUsage


def _request(
    *,
    tmp_path: Path,
    execution_id: str,
    code: str,
    budget: ResourceBudget,
) -> SupervisedExecutionRequest:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    return SupervisedExecutionRequest(
        execution_id=execution_id,
        host_command=[sys.executable, "-c", code],
        cwd=workspace,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(run_dir / "home"),
            "PYTHONUNBUFFERED": "1",
        },
        run_dir=run_dir,
        action_id="action-1",
        stage="test_supervisor",
        profile_id="test-local",
        backend="local",
        budget=budget,
    )


def test_large_stdout_is_drained_but_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(settings, "runs_dir", runs_dir)
    request = _request(
        tmp_path=tmp_path,
        execution_id="exec_large_output",
        code="import os; os.write(1, b'x' * 1000000)",
        budget=ResourceBudget(
            max_wall_time_seconds=10,
            max_processes=4,
            max_log_bytes_per_stream=4096,
            max_preview_bytes=1024,
            sample_interval_seconds=0.05,
            terminate_grace_seconds=0.2,
        ),
    )

    result = ProcessSupervisor().execute(request)

    assert result.ok is True
    assert result.log_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 1024
    assert Path(result.stdout_path).stat().st_size == 4096


def test_budget_reason_is_deterministic() -> None:
    usage = ResourceUsage(
        peak_rss_bytes=200,
        peak_process_count=2,
        total_cpu_seconds=1,
        total_write_bytes=10,
        samples=1,
    )
    budget = ResourceBudget(
        max_wall_time_seconds=10,
        max_memory_bytes=100,
        max_processes=4,
        max_log_bytes_per_stream=4096,
        max_preview_bytes=1024,
    )

    assert budget_end_reason(usage, budget) == "memory_limit"


def test_timeout_kills_child_process_group(
    tmp_path,
    monkeypatch,
) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(settings, "runs_dir", runs_dir)
    child_pid_path = tmp_path / "child.pid"
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import pathlib, subprocess, sys, time; "
        f"p=subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(p.pid)); "
        "time.sleep(60)"
    )
    request = _request(
        tmp_path=tmp_path,
        execution_id="exec_timeout",
        code=parent_code,
        budget=ResourceBudget(
            max_wall_time_seconds=0.5,
            max_processes=8,
            max_log_bytes_per_stream=4096,
            max_preview_bytes=1024,
            sample_interval_seconds=0.05,
            terminate_grace_seconds=0.2,
        ),
    )

    result = ProcessSupervisor().execute(request)
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))

    deadline = time.monotonic() + 3
    while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
        try:
            if psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE:
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.05)

    assert result.end_reason == "timeout"
    if psutil.pid_exists(child_pid):
        assert psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE
