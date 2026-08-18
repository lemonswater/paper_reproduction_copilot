from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas import ArtifactRecord
from app.tools.artifact_tools import (
    artifact_state_update,
    inspect_artifact_records,
    resolve_artifact_path,
    write_json_artifact,
    write_text_artifact,
)


def test_write_artifact_is_inside_current_run(run_state):
    path, record = write_json_artifact(
        state=run_state,
        relative_path="analysis/demo.json",
        payload={"value": 1},
        producer_node="test_node",
    )

    run_dir = Path(run_state["run_dir"]).resolve()
    assert run_dir in path.resolve().parents
    assert record.relative_path == "analysis/demo.json"
    assert record.layer == "analysis"
    assert record.producer_node == "test_node"
    assert record.sha256
    assert record.size_bytes > 0


@pytest.mark.parametrize(
    "relative_path",
    [
        "/data/tianshaoqi24/outside.json",
        "../outside.json",
        "analysis/../../outside.json",
        "unknown/file.json",
        "single-file.json",
    ],
)
def test_artifact_path_escape_is_rejected(
    run_state,
    relative_path,
):
    with pytest.raises(ValueError):
        resolve_artifact_path(run_state, relative_path)


def test_artifact_records_are_upserted_by_relative_path(run_state):
    _, first_record = write_text_artifact(
        state=run_state,
        relative_path="analysis/demo.txt",
        text="first",
        producer_node="first_node",
    )
    first_update = artifact_state_update(
        run_state,
        [first_record],
    )
    working_state = {**run_state, **first_update}

    _, second_record = write_text_artifact(
        state=working_state,
        relative_path="analysis/demo.txt",
        text="second",
        producer_node="second_node",
    )
    second_update = artifact_state_update(
        working_state,
        [second_record],
    )

    matching = [
        item
        for item in second_update["artifact_records"]
        if item["relative_path"] == "analysis/demo.txt"
    ]
    assert len(matching) == 1
    assert matching[0]["producer_node"] == "second_node"
    assert Path(matching[0]["absolute_path"]).read_text() == "second"


def test_inspect_artifact_detects_hash_mismatch(run_state):
    path, record = write_text_artifact(
        state=run_state,
        relative_path="analysis/tamper.txt",
        text="before",
        producer_node="test_node",
    )
    working_state = {
        **run_state,
        **artifact_state_update(run_state, [record]),
    }

    path.write_text("after", encoding="utf-8")
    inspected, issues = inspect_artifact_records(working_state)

    item = next(
        entry
        for entry in inspected
        if entry["relative_path"] == "analysis/tamper.txt"
    )
    assert item["integrity_status"] == "hash_mismatch"
    assert any(
        issue["code"] == "ARTIFACT_HASH_MISMATCH"
        for issue in issues
    )


def test_artifact_record_schema_rejects_negative_size():
    with pytest.raises(ValueError):
        ArtifactRecord(
            artifact_id="artifact_demo",
            run_id="run_demo",
            layer="analysis",
            relative_path="analysis/demo.json",
            absolute_path="/data/tianshaoqi24/demo/analysis/demo.json",
            media_type="application/json",
            sha256="a" * 64,
            size_bytes=-1,
            producer_node="test",
            created_at="2026-07-24T00:00:00+00:00",
        )
