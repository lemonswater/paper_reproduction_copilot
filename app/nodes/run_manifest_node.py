import json
from pathlib import Path

from app.tools.artifact_tools import (
    build_run_id,
    build_run_manifest,
    create_run_layout,
    snapshot_output_files,
)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    """
    output_files 是一个不断 append 的列表。
    这里做一个保序去重，避免 manifest 自己重复追加多次。
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def run_manifest_node(state: dict) -> dict:
    """
    把本次运行的 output_files 归档到 runs/<run_id>/，
    然后生成 artifact_index.json 和 run_manifest.json。
    """
    run_id = state.get("run_id") or build_run_id(state.get("task_id"))
    layout = create_run_layout(run_id)
    run_dir = Path(state.get("run_dir") or layout["run_root"])
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    original_output_files = state.get("output_files", [])
    artifact_records = snapshot_output_files(original_output_files, str(run_dir))

    artifact_index_path = reports_dir / "artifact_index.json"
    artifact_index_path.write_text(
        json.dumps(artifact_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = build_run_manifest(
        {
            **state,
            "run_id": run_id,
            "run_dir": str(run_dir),
        },
        artifact_records,
    )
    run_manifest_path = reports_dir / "run_manifest.json"
    run_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    updated_output_files = _dedupe_preserve_order(
        [
            *original_output_files,
            str(artifact_index_path),
            str(run_manifest_path),
        ]
    )

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "artifact_records": artifact_records,
        "artifact_index_path": str(artifact_index_path),
        "run_manifest_path": str(run_manifest_path),
        "output_files": updated_output_files,
    }