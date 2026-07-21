import hashlib
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from app.config import settings


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "run"


def build_run_id(task_id: str | None) -> str:
    prefix = _slugify(task_id or "run")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{timestamp}-{suffix}"


def create_run_layout(run_id: str) -> dict[str, str]:
    run_root = settings.runs_dir / run_id
    layout = {
        "run_root": str(run_root),
        "analysis_dir": str(run_root / "analysis"),
        "planning_dir": str(run_root / "planning"),
        "execution_dir": str(run_root / "execution"),
        "debug_dir": str(run_root / "debug"),
        "reports_dir": str(run_root / "reports"),
    }

    for path in layout.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    return layout


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def try_get_git_commit(repo_path: str | None) -> str | None:
    if not repo_path:
        return None

    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        return None

    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    commit = result.stdout.strip()
    return commit or None


def classify_output_file(path: str) -> str:
    name = Path(path).name

    if name in {
        "paper_summary.json",
        "method_modules.json",
        "repo_map.json",
        "repo_summary.md",
        "paper_code_mapping.json",
        "paper_code_mapping.md"
    }:
        return "analysis"

    if name in {
        "experiment_plan.json",
        "experiment_plan.md",
        "command_selection_input.json",
        "command_selection_record.json",
        "effective_run_commands.json",
        "preflight_report.json",
        "preflight_report.md"
    }:
        return "planning"

    if name in {
        "execution.log",
        "smoke_test.log",
        "smoke_test_report.json",
        "smoke_test_report.md",
    }:
        return "execution"

    if name in {
        "debug_report.json",
        "debug_report.md",
        "repair_proposal.json",
        "repair_proposal.md",
    }:
        return "debug"

    if name in {"final_report.md", "eval_report.json", "eval_report.md"}:
        return "reports"

    return "reports"


def snapshot_output_files(output_files: list[str], run_root: str) -> list[dict[str, Any]]:
    run_root_path = Path(run_root).resolve()
    seen: set[str] = set()
    records: list[dict[str, Any]] = []

    for index, raw_path in enumerate(output_files):
        if raw_path in seen:
            continue
        seen.add(raw_path)

        artifact_type = classify_output_file(raw_path)
        source_path = Path(raw_path)

        if source_path.exists():
            resolved_source = source_path.resolve()
            if resolved_source == run_root_path or run_root_path in resolved_source.parents:
                records.append(
                    {
                        "source_path": str(source_path),
                        "artifact_type": artifact_type,
                        "status": "skipped_internal",
                        "dest_path": None,
                        "sha256": None,
                    }
                )
                continue

        if not source_path.exists():
            records.append(
                {
                    "source_path": str(source_path),
                    "artifact_type": artifact_type,
                    "status": "missing",
                    "dest_path": None,
                    "sha256": None,
                }
            )
            continue

        target_dir = run_root_path / artifact_type
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_path = target_dir / source_path.name
        if dest_path.exists():
            # 如果未来出现同名文件，简单加前缀避免覆盖。
            dest_path = target_dir / f"{index:02d}_{source_path.name}"

        shutil.copy2(source_path, dest_path)

        records.append(
            {
                "source_path": str(source_path),
                "artifact_type": artifact_type,
                "status": "copied",
                "dest_path": str(dest_path),
                "sha256": sha256_file(dest_path),
            }
        )

    return records


def build_run_manifest(state: dict[str, Any], artifact_records: list[dict[str, Any]]) -> dict[str, Any]:
    selected_index = state.get("selected_run_command_index")
    effective_commands = state.get("edited_run_commands") or state.get("run_commands") or []

    selected_command = None
    if isinstance(selected_index, int) and 0 <= selected_index < len(effective_commands):
        selected_command = effective_commands[selected_index]

    copied_count = sum(1 for item in artifact_records if item.get("status") == "copied")
    missing_count = sum(1 for item in artifact_records if item.get("status") == "missing")

    return {
        "run_id": state.get("run_id"),
        "task_id": state.get("task_id"),
        "run_dir": state.get("run_dir"),
        "run_started_at": state.get("run_started_at"),
        "manifest_generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_path": state.get("paper_path"),
        "repo_path": state.get("repo_path"),
        "repo_git_commit": try_get_git_commit(state.get("repo_path")),
        "experiment_goal": state.get("experiment_goal"),
        "final_status": state.get("final_status"),
        "selected_run_command_index": selected_index,
        "selected_run_command": selected_command,
        "command_selection_record": state.get("command_selection_record"),
        "pending_action_hash": state.get("pending_action_hash"),
        "approval": {
            "decision": state.get("user_approval"),
            "feedback": state.get("human_feedback"),
            "record": state.get("approval_record"),
        },
        "execution": {
            "log_path": state.get("execution_log_path") or state.get("log_path"),
            "result": state.get("execution_result"),
        },
        "artifacts": {
            "count": len(artifact_records),
            "copied_count": copied_count,
            "missing_count": missing_count,
            "items": artifact_records,
        },
        "smoke_test": {
            "status": state.get("smoke_test_status"),
            "passed": state.get("smoke_test_passed"),
            "log_path": state.get("smoke_test_log_path"),
            "report": state.get("smoke_test_report"),
        },
        "repair": {
            "attempt_count": state.get("repair_attempt_count", 0),
            "history": state.get("repair_history", []),
            "proposal": state.get("repair_proposal"),
        },
        "output_files": state.get("output_files", []),
    }
