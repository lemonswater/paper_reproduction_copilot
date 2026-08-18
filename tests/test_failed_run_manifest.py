from __future__ import annotations

import json
from pathlib import Path

from app.nodes.final_report_node import final_report_node
from app.nodes.run_manifest_node import run_manifest_node
from app.tools.artifact_tools import (
    artifact_state_update,
    write_text_artifact,
)
from app.tools.error_tools import (
    build_stage_error,
    persist_stage_errors,
)


def test_failed_run_still_has_error_final_and_manifest(run_state):
    error = build_stage_error(
        stage="input_validation",
        code="PAPER_NOT_FOUND",
        category="user",
        message="paper is missing",
        terminal=True,
    )
    state = {
        **run_state,
        **persist_stage_errors(
            state=run_state,
            new_errors=[error],
        ),
    }
    state.update(final_report_node(state))
    state.update(run_manifest_node(state))

    run_dir = Path(state["run_dir"])
    assert (run_dir / "reports" / "error_report.json").exists()
    assert (run_dir / "reports" / "error_report.md").exists()
    assert (run_dir / "reports" / "final_report.md").exists()
    assert (run_dir / "reports" / "artifact_index.json").exists()
    assert (run_dir / "reports" / "run_manifest.json").exists()

    manifest = json.loads(
        (run_dir / "reports" / "run_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["final_status"] == "invalid_input"
    assert manifest["errors"]["terminal_count"] == 1
    assert all(
        Path(item["absolute_path"]).resolve().is_relative_to(
            run_dir.resolve()
        )
        for item in manifest["artifacts"]["items"]
    )


def test_manifest_records_tampered_artifact_and_still_writes(
    run_state,
):
    path, record = write_text_artifact(
        state=run_state,
        relative_path="analysis/source.txt",
        text="original",
        producer_node="fixture",
    )
    state = {
        **run_state,
        **artifact_state_update(run_state, [record]),
        "final_status": "succeeded",
    }
    path.write_text("tampered", encoding="utf-8")

    result = run_manifest_node(state)
    manifest_path = Path(result["run_manifest_path"])

    assert manifest_path.exists()
    assert result["final_status"] == "agent_failed"
    assert any(
        item["code"] == "ARTIFACT_HASH_MISMATCH"
        for item in result["stage_errors"]
    )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    tampered = next(
        item
        for item in manifest["artifacts"]["items"]
        if item["relative_path"] == "analysis/source.txt"
    )
    assert tampered["integrity_status"] == "hash_mismatch"