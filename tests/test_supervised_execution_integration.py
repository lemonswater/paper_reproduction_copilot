from __future__ import annotations

import json
import sys
from pathlib import Path

from app.config import settings
from app.execution.local_runner import LocalRunner
from app.schemas import ExecutableAction, ExecutionProfile


def test_local_runner_child_cannot_read_agent_api_key(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    workspace.mkdir()
    run_dir.mkdir(parents=True)

    script = workspace / "show_secret.py"
    script.write_text(
        "import os\n"
        "print(os.getenv('OPENAI_API_KEY', '<missing>'))\n",
        encoding="utf-8",
    )
    python_dir = str(Path(sys.executable).resolve().parent)
    program = Path(sys.executable).name
    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(runs_dir),
        inherited_env_keys=[],
        env={"PATH": python_dir, "LANG": "C.UTF-8"},
        allowed_programs=[program],
        writable_roots=[str(workspace)],
    )
    action = ExecutableAction(
        action_id="action-secret-test",
        program=program,
        args=[script.name],
        cwd=str(workspace),
        source="script",
        reason="verify minimal env",
        timeout_seconds=10,
        writable_paths=[str(workspace)],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint="test-hash",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    result = LocalRunner(profile).run(
        action.model_dump(),
        run_dir=str(run_dir),
        stage="secret_test",
    )

    assert result["ok"] is True
    assert result["stdout"].strip() == "<missing>"
    process_record = json.loads(
        Path(result["process_record_path"]).read_text(
            encoding="utf-8"
        )
    )
    all_keys = {
        *process_record["inherited_env_keys"],
        *process_record["profile_env_keys"],
        *process_record["action_env_keys"],
    }
    assert "OPENAI_API_KEY" not in all_keys
