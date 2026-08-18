from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.nodes.smoke_test_node import smoke_test_node


def _action(repo_dir: Path, args: list[str]) -> dict:
    return {
        "action_id": "action_demo",
        "action_type": "run_command",
        "program": "python",
        "args": args,
        "cwd": str(repo_dir),
        "source": "script",
        "reason": "test",
        "timeout_seconds": 300,
        "env_overrides": {},
        "writable_paths": [str(repo_dir)],
        "network_access": "none",
        "resource_budget": None,
        "execution_profile_id": "test-local",
        "execution_profile_fingerprint": "profile-hash",
    }


def _supervisor_result(
    run_state,
    *,
    ok: bool,
    end_reason: str = "exited",
) -> dict:
    attempt = (
        Path(run_state["run_dir"])
        / "execution"
        / "attempts"
        / "smoke-test"
    )
    attempt.mkdir(parents=True)
    stdout_path = attempt / "stdout.log"
    stderr_path = attempt / "stderr.log"
    combined_path = attempt / "combined.log"
    record_path = attempt / "process_record.json"
    stdout_path.write_text("smoke ok\n" if ok else "", encoding="utf-8")
    stderr_path.write_text("" if ok else "CUDA OOM\n", encoding="utf-8")
    combined_path.write_text("smoke output\n", encoding="utf-8")
    record_path.write_text("{}\n", encoding="utf-8")
    return {
        "ok": ok,
        "returncode": 0 if ok else 1,
        "end_reason": end_reason,
        "stdout": "smoke ok\n" if ok else "",
        "stderr": "" if ok else "CUDA OOM",
        "combined_output": "smoke output",
        "timeout": end_reason == "timeout",
        "cancelled": end_reason == "cancelled",
        "cancellation_reason": None,
        "log_truncated": False,
        "execution_id": "smoke-test",
        "resource_usage": {"peak_rss_bytes": 128},
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "combined_log_path": str(combined_path),
        "process_record_path": str(record_path),
    }


def test_smoke_test_node_runs_reduced_action_and_writes_report(
    tmp_path,
    run_state,
):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state = {
        **run_state,
        "pending_action": _action(
            repo_dir,
            [
                "train.py",
                "--batch_size",
                "8",
                "--epochs",
                "100",
                "--num_workers",
                "8",
            ],
        ),
        "pending_action_hash": "hash_demo",
    }
    fake_result = _supervisor_result(run_state, ok=True)

    with patch(
        "app.nodes.smoke_test_node.run_action_safe",
        return_value=fake_result,
    ) as mocked_run:
        result = smoke_test_node(state)

    smoke_action = mocked_run.call_args.args[0]
    mocked_run.assert_called_once_with(
        smoke_action,
        state=state,
        stage="smoke_test",
    )
    assert result["smoke_test_status"] == "passed"
    assert result["smoke_test_passed"] is True
    assert result["smoke_test_log_path"] == fake_result["combined_log_path"]
    assert smoke_action["network_access"] == "none"
    assert smoke_action["writable_paths"] == [str(repo_dir)]
    report = result["smoke_test_report"]
    assert "--batch_size -> 1" in report["applied_overrides"]
    assert "--epochs -> 1" in report["applied_overrides"]
    assert "--num_workers -> 0" in report["applied_overrides"]


def test_smoke_test_node_skips_when_no_safe_reduction_found(
    tmp_path,
    run_state,
):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state = {
        **run_state,
        "pending_action": _action(
            repo_dir,
            ["eval.py", "--config", "configs/eval.yaml"],
        ),
        "pending_action_hash": "hash_demo",
    }

    with patch("app.nodes.smoke_test_node.run_action_safe") as mocked_run:
        result = smoke_test_node(state)

    mocked_run.assert_not_called()
    assert result["smoke_test_status"] == "skipped"
    assert result["smoke_test_passed"] is True


def test_smoke_test_node_sets_log_path_when_failed(
    tmp_path,
    run_state,
):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    state = {
        **run_state,
        "pending_action": _action(
            repo_dir,
            ["train.py", "--batch_size", "8"],
        ),
        "pending_action_hash": "hash_demo",
    }
    fake_result = _supervisor_result(run_state, ok=False)

    with patch(
        "app.nodes.smoke_test_node.run_action_safe",
        return_value=fake_result,
    ):
        result = smoke_test_node(state)

    assert result["smoke_test_status"] == "failed"
    assert result["log_path"] == fake_result["combined_log_path"]
    assert result["final_status"] == "failed"
    assert result["active_stage_error"]["category"] == "paper_program"
