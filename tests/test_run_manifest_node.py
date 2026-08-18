from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.tools.artifact_tools import (
    artifact_state_update,
    sha256_file,
    write_json_artifact,
    write_text_artifact,
)


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


def test_run_manifest_node_indexes_registered_run_artifacts(
    tmp_path,
    run_state,
):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        **run_state,
        "job_id": "job-manifest-test",
        "thread_id": "thread-manifest-test",
        "task_id": "paper-001",
        "run_started_at": "2026-07-16T00:00:00+00:00",
        "paper_path": "pdf/demo.pdf",
        "repo_path": str(repo_dir),
        "experiment_goal": "复现论文 main result",
        "final_status": "succeeded",
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
        "capability_decision": {"allowed": True},
        "capability_report_path": "planning/capability_decision.json",
        "active_execution_id": "exec-test",
        "active_process_record_path": "execution/process_record.json",
        "execution_end_reason": "exited",
        "execution_resource_usage": {"peak_rss_bytes": 1024},
        "cancellation_requested": False,
        "execution_result": {
            "ok": True,
            "returncode": 0,
        },
        "execution_evidence": {
            "evidence_id": "exec-evidence-fixture",
            "evidence_sha256": "a" * 64,
            "action_id": "action-fixture",
            "action_sha256": "b" * 64,
            "end_reason": "exited",
            "returncode": 0,
        },
        "execution_verification": {
            "verification_id": "exec-verification-fixture",
            "claim_scope": "execution_protocol",
            "verdict": "verified",
            "projected_final_status": "succeeded",
            "evidence_sha256": "a" * 64,
            "verification_sha256": "c" * 64,
        },
        "execution_verification_hash": "c" * 64,
    }

    _, analysis_record = write_json_artifact(
        state=state,
        relative_path="analysis/paper_summary.json",
        payload={"title": "demo"},
        producer_node="method_extractor",
    )
    _, report_record = write_text_artifact(
        state=state,
        relative_path="reports/final_report.md",
        text="# Final Report\n",
        producer_node="final_report",
        media_type="text/markdown",
    )
    state.update(
        artifact_state_update(
            state,
            [analysis_record, report_record],
        )
    )

    result = run_manifest_node(state)

    artifact_index_path = Path(result["artifact_index_path"])
    run_manifest_path = Path(result["run_manifest_path"])

    assert artifact_index_path.exists()
    assert run_manifest_path.exists()

    artifact_index = json.loads(artifact_index_path.read_text(encoding="utf-8"))
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    indexed_artifacts = artifact_index["artifacts"]
    assert artifact_index["run_id"] == run_state["run_id"]
    assert artifact_index["artifact_count"] == len(indexed_artifacts)
    assert any(
        item["relative_path"] == "analysis/paper_summary.json"
        and item["layer"] == "analysis"
        and item["producer_node"] == "method_extractor"
        and item["integrity_status"] == "current"
        for item in indexed_artifacts
    )
    assert any(
        item["relative_path"] == "reports/final_report.md"
        and item["layer"] == "reports"
        and item["producer_node"] == "final_report"
        and item["integrity_status"] == "current"
        for item in indexed_artifacts
    )

    assert manifest["manifest_version"] == 5
    assert manifest["run_id"] == run_state["run_id"]
    assert manifest["final_status"] == "succeeded"
    assert manifest["execution"]["evidence"][
        "evidence_sha256"
    ] == "a" * 64
    assert manifest["execution"]["verification"][
        "claim_scope"
    ] == "execution_protocol"
    assert manifest["execution"][
        "verification_sha256"
    ] == "c" * 64
    assert manifest["selected_run_command"]["command"] == "python train.py --dataset_path /data/demo"
    assert manifest["pending_action_hash"] == "hash-demo"
    assert manifest["capability_policy"]["decision"]["allowed"] is True
    supervision = manifest["execution_supervision"]
    assert supervision["execution_id"] == "exec-test"
    assert supervision["end_reason"] == "exited"
    assert supervision["security_semantics"]["minimal_environment"] is True
    assert supervision["security_semantics"]["network_os_enforced"] is False
    assert manifest["artifacts"]["issue_count"] == 0
    assert manifest["artifacts"]["current_count"] == (
        manifest["artifacts"]["count"]
    )

    run_dir = Path(run_state["run_dir"])
    assert artifact_index_path.parent == run_dir / "reports"
    assert run_manifest_path.parent == run_dir / "reports"
    assert all(
        record["run_id"] == run_state["run_id"]
        for record in result["artifact_records"]
    )
    assert all(
        run_dir in Path(record["absolute_path"]).parents
        for record in result["artifact_records"]
    )
    assert all(
        record["sha256"]
        == sha256_file(Path(record["absolute_path"]))
        for record in result["artifact_records"]
    )


def test_manifest_allows_legacy_sync_run_without_job_identity(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    state = {
        "task_id": "legacy-sync",
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
        "final_status": "succeeded",
    }
    state.update(run_context_node(state))

    result = run_manifest_node(state)
    manifest = json.loads(
        Path(
            result["run_manifest_path"]
        ).read_text(encoding="utf-8")
    )

    assert manifest["manifest_version"] == 5
    assert manifest["job_id"] is None
    assert manifest["thread_id"] is None
    assert manifest["execution"]["evidence"] is None
    assert manifest["execution"]["verification"] is None
    assert manifest["execution"]["verification_sha256"] is None
