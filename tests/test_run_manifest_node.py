import json
from pathlib import Path

from app.config import settings
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node


def test_run_context_node_creates_run_id_and_run_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    result = run_context_node({"task_id": "paper-001"})

    assert result["run_id"].startswith("paper-001-")
    assert Path(result["run_dir"]).exists()
    assert (Path(result["run_dir"]) / "analysis").exists()
    assert (Path(result["run_dir"]) / "planning").exists()
    assert (Path(result["run_dir"]) / "execution").exists()
    assert (Path(result["run_dir"]) / "debug").exists()
    assert (Path(result["run_dir"]) / "reports").exists()
    assert result["run_started_at"]


def test_run_context_node_reuses_existing_run_on_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    existing_run_dir = tmp_path / "runs" / "demo-run"
    state = {
        "run_id": "demo-run",
        "run_dir": str(existing_run_dir),
        "run_started_at": "2026-07-16T00:00:00+00:00",
    }

    result = run_context_node(state)

    assert result["run_id"] == "demo-run"
    assert result["run_dir"] == str(existing_run_dir)
    assert result["run_started_at"] == "2026-07-16T00:00:00+00:00"
    assert existing_run_dir.exists()


def test_run_manifest_node_snapshots_outputs_and_writes_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    paper_summary_path = outputs_dir / "paper_summary.json"
    final_report_path = outputs_dir / "final_report.md"

    paper_summary_path.write_text('{"title": "demo"}', encoding="utf-8")
    final_report_path.write_text("# Final Report\n", encoding="utf-8")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "task_id": "paper-001",
        "run_id": "paper-001-demo",
        "run_dir": str(tmp_path / "runs" / "paper-001-demo"),
        "run_started_at": "2026-07-16T00:00:00+00:00",
        "paper_path": "pdf/demo.pdf",
        "repo_path": str(repo_dir),
        "experiment_goal": "复现论文 main result",
        "final_status": "succeeded",
        "output_files": [
            str(paper_summary_path),
            str(final_report_path),
        ],
        "run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo",
                "cwd": str(repo_dir),
                "source": "readme",
                "risk_level": "high",
                "reason": "demo command",
            }
        ],
        "selected_run_command_index": 0,
        "command_selection_record": {
            "selected_index": 0,
            "edits": [],
            "original_count": 1,
            "reviewed_at": "2026-07-16T00:00:00+00:00",
        },
        "pending_action_hash": "hash-demo",
        "user_approval": "approved",
        "human_feedback": "looks good",
        "approval_record": {
            "decision": "approved",
            "action_hash": "hash-demo",
        },
        "execution_result": {
            "ok": True,
            "returncode": 0,
        },
        "execution_log_path": str(outputs_dir / "execution.log"),
    }

    result = run_manifest_node(state)

    artifact_index_path = Path(result["artifact_index_path"])
    run_manifest_path = Path(result["run_manifest_path"])

    assert artifact_index_path.exists()
    assert run_manifest_path.exists()

    artifact_index = json.loads(artifact_index_path.read_text(encoding="utf-8"))
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    assert any(item["artifact_type"] == "analysis" for item in artifact_index)
    assert any(item["artifact_type"] == "reports" for item in artifact_index)

    assert manifest["run_id"] == "paper-001-demo"
    assert manifest["final_status"] == "succeeded"
    assert manifest["selected_run_command"]["command"] == "python train.py --dataset_path /data/demo"
    assert manifest["pending_action_hash"] == "hash-demo"

    analysis_copy = Path(state["run_dir"]) / "analysis" / "paper_summary.json"
    report_copy = Path(state["run_dir"]) / "reports" / "final_report.md"

    assert analysis_copy.exists()
    assert report_copy.exists()