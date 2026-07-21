from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.nodes.smoke_test_node import smoke_test_node


def test_smoke_test_node_runs_reduced_action_and_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": [
                "train.py",
                "--batch_size", "8",
                "--epochs", "100",
                "--num_workers", "8",
            ],
            "cwd": str(repo_dir),
            "source": "manual",
            "reason": "test",
            "timeout_seconds": 300,
            "env_allowlist": {},
            "writable_paths": [str(repo_dir)],
        },
        "pending_action_hash": "hash_demo",
        "output_files": [],
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "stdout": "smoke ok\n",
        "stderr": "",
        "combined_output": "smoke ok\n",
    }

    with patch("app.nodes.smoke_test_node.run_action_safe", return_value=fake_result):
        result = smoke_test_node(state)

    assert result["smoke_test_status"] == "passed"
    assert result["smoke_test_passed"] is True
    assert Path(result["smoke_test_log_path"]).exists()

    report = result["smoke_test_report"]
    assert "--batch_size -> 1" in report["applied_overrides"]
    assert "--epochs -> 1" in report["applied_overrides"]
    assert "--num_workers -> 0" in report["applied_overrides"]


def test_smoke_test_node_skips_when_no_safe_reduction_found(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["eval.py", "--config", "configs/eval.yaml"],
            "cwd": str(repo_dir),
            "source": "manual",
            "reason": "test",
            "timeout_seconds": 300,
            "env_allowlist": {},
            "writable_paths": [str(repo_dir)],
        },
        "pending_action_hash": "hash_demo",
        "output_files": [],
    }

    result = smoke_test_node(state)

    assert result["smoke_test_status"] == "skipped"
    assert result["smoke_test_passed"] is True
    assert any(path.endswith("smoke_test_report.json") for path in result["output_files"])


def test_smoke_test_node_sets_log_path_when_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py", "--batch_size", "8"],
            "cwd": str(repo_dir),
            "source": "manual",
            "reason": "test",
            "timeout_seconds": 300,
            "env_allowlist": {},
            "writable_paths": [str(repo_dir)],
        },
        "pending_action_hash": "hash_demo",
        "output_files": [],
    }

    fake_result = {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "RuntimeError: CUDA out of memory",
        "combined_output": "RuntimeError: CUDA out of memory",
    }

    with patch("app.nodes.smoke_test_node.run_action_safe", return_value=fake_result):
        result = smoke_test_node(state)

    assert result["smoke_test_status"] == "failed"
    assert result["log_path"].endswith("smoke_test.log")
    assert result["final_status"] == "failed"