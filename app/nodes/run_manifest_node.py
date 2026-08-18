from __future__ import annotations

from typing import Any

from app.tools.artifact_tools import (
    artifact_state_update,
    build_run_manifest,
    inspect_artifact_records,
    write_json_artifact,
)
from app.tools.error_tools import (
    build_stage_error,
    persist_stage_errors,
)


def run_manifest_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    只索引当前 run 已登记的 Artifact，不再从共享 outputs/ 复制文件。

    Artifact 不完整时仍生成 Manifest，并把完整性问题记录为 StageError。
    """

    working_state = dict(state)
    inspected, issues = inspect_artifact_records(working_state)

    if issues:
        integrity_errors = [
            build_stage_error(
                stage="run_manifest",
                code=issue["code"],
                category="agent",
                message=issue["message"],
                terminal=True,
            )
            for issue in issues
        ]
        error_update = persist_stage_errors(
            state=working_state,
            new_errors=integrity_errors,
        )
        working_state.update(error_update)

        # Error Report 被原子重写并重新登记后，再基于当前事实检查一次。
        inspected, _ = inspect_artifact_records(working_state)

    index_path, index_record = write_json_artifact(
        state=working_state,
        relative_path="reports/artifact_index.json",
        payload={
            "run_id": working_state.get("run_id"),
            "artifact_count": len(inspected),
            "artifacts": inspected,
        },
        producer_node="run_manifest",
    )

    index_item = {
        **index_record.model_dump(),
        "integrity_status": "current",
        "integrity_detail": "",
    }
    manifest_artifacts = [*inspected, index_item]
    manifest = build_run_manifest(
        working_state,
        manifest_artifacts,
    )

    manifest_path, manifest_record = write_json_artifact(
        state=working_state,
        relative_path="reports/run_manifest.json",
        payload=manifest,
        producer_node="run_manifest",
    )

    final_artifact_update = artifact_state_update(
        working_state,
        [index_record, manifest_record],
    )
    return {
        "run_id": working_state["run_id"],
        "run_dir": working_state["run_dir"],
        "stage_errors": working_state.get("stage_errors", []),
        "active_stage_error": working_state.get(
            "active_stage_error"
        ),
        "error": working_state.get("error"),
        "final_status": working_state.get("final_status"),
        "artifact_index_path": str(index_path),
        "run_manifest_path": str(manifest_path),
        **final_artifact_update,
    }
