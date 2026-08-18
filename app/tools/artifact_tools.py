from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from app.config import settings
from app.schemas import ArtifactRecord
from app.secrets.redaction import SecretRedactor
from app.workspace.paths import (
    create_run_layout_at,
    require_managed_run_root,
)

ARTIFACT_LAYERS = {
    "inputs",
    "analysis",
    "planning",
    "execution",
    "debug",
    "patches",
    "reports",
    "traces",
}


def utc_now() -> str:
    """统一使用 UTC ISO-8601，便于跨时区比较和排序。"""

    return datetime.now(timezone.utc).isoformat()

def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "run"

def build_run_id(task_id: str | None) -> str:
    prefix = _slugify(task_id or "run")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{timestamp}-{suffix}"

def create_run_layout(
    run_id: str,
    *,
    run_root_override: str | Path | None = None,
) -> dict[str, str]:
    """
    创建当前 run 的标准目录。

    run_id 只允许作为一个目录名，不能携带 /、.. 或绝对路径。
    Phase 26 起 run_root 可来自 worker workspace（跨 host 物化目录）。
    """

    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError(f"无效的 run_id：{run_id!r}")

    if run_root_override is None:
        run_root = (settings.runs_dir / run_id).resolve()
    else:
        run_root = Path(run_root_override).expanduser().resolve()

    return create_run_layout_at(run_root)

def require_run_root(state: dict[str, Any]) -> Path:
    """
    读取并校验 state.run_dir。

    Phase 26 之后 run_dir 可位于 RUNS_DIR 或 worker workspace root 内。
    """

    raw_run_dir = state.get("run_dir")
    if not raw_run_dir:
        raise ValueError("当前 state 缺少 run_dir")

    run_root = require_managed_run_root(str(raw_run_dir))
    run_root.mkdir(parents=True, exist_ok=True)
    return run_root

def resolve_artifact_path(
    state: dict[str, Any],
    relative_path: str,
) -> Path:
    """
    把 run 内相对路径解析为绝对路径。

    只允许：
      analysis/paper_summary.json
      execution/execution.log

    拒绝：
      /absolute/path
      ../outside
      reports/../../outside
      unknown_layer/file.json
    """

    posix_path = PurePosixPath(relative_path)
    if posix_path.is_absolute():
        raise ValueError("Artifact relative_path 不能是绝对路径")
    if ".." in posix_path.parts:
        raise ValueError("Artifact relative_path 不能包含 ..")
    if len(posix_path.parts) < 2:
        raise ValueError("Artifact 路径必须包含 layer 和文件名")
    if posix_path.parts[0] not in ARTIFACT_LAYERS:
        raise ValueError(
            f"未知 Artifact layer：{posix_path.parts[0]}"
        )

    run_root = require_run_root(state)
    target = run_root.joinpath(*posix_path.parts).resolve()
    if target == run_root or run_root not in target.parents:
        raise ValueError("Artifact 路径逃逸当前 run")

    return target

def artifact_dir(
    state: dict[str, Any],
    layer: str,
    *parts: str,
) -> Path:
    """给需要自行生成多个文件的旧工具提供受控目录。"""

    suffix = "/".join((layer, *parts, ".directory-marker"))
    marker = resolve_artifact_path(state, suffix)
    directory = marker.parent
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def sha256_file(path: Path) -> str:
    """计算磁盘文件 SHA-256；文件不存在时由 open() 明确报错。"""

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


def try_is_git_clean(repo_path: str | None) -> bool | None:
    """返回受管仓库是否 clean；无法确认时返回 None，不猜测。"""

    if not repo_path:
        return None
    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        return None
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "status",
            "--porcelain",
            "--untracked-files=normal",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return not result.stdout.strip()


def build_run_manifest(
    state: dict[str, Any],
    artifact_records: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_index = state.get("selected_run_command_index")
    effective_commands = (
        state.get("edited_run_commands")
        or state.get("run_commands")
        or []
    )

    selected_command = None
    if (
        isinstance(selected_index, int)
        and 0 <= selected_index < len(effective_commands)
    ):
        selected_command = effective_commands[selected_index]

    stage_errors = list(state.get("stage_errors", []))
    terminal_errors = [
        item
        for item in stage_errors
        if item.get("terminal") is True
    ]
    current_count = sum(
        1
        for item in artifact_records
        if item.get("integrity_status", "current") == "current"
    )

    return {
        "manifest_version": 5,
        "job_id": state.get("job_id"),
        "thread_id": state.get("thread_id"),
        "run_id": state.get("run_id"),
        "task_id": state.get("task_id"),
        "run_dir": state.get("run_dir"),
        "run_started_at": state.get("run_started_at"),
        "manifest_generated_at": utc_now(),
        "paper_path": state.get("paper_path"),
        "repo_path": state.get("repo_path"),
        "repo_git_commit": try_get_git_commit(
            state.get("repo_path")
        ),
        "experiment_goal": state.get("experiment_goal"),
        "final_status": state.get("final_status"),
        "inputs_validated": state.get("inputs_validated", False),
        "execution_profile": {
            "profile_id": state.get("execution_profile_id"),
            "fingerprint": state.get(
                "execution_profile_fingerprint"
            ),
        },
        "capability_policy": {
            "decision": state.get("capability_decision"),
            "report_path": state.get("capability_report_path"),
        },
        "execution_supervision": {
            "execution_id": state.get("active_execution_id"),
            "process_record_path": state.get(
                "active_process_record_path"
            ),
            "end_reason": state.get("execution_end_reason"),
            "resource_usage": state.get(
                "execution_resource_usage"
            ),
            "cancellation_requested": state.get(
                "cancellation_requested",
                False,
            ),
            "cancellation_reason": state.get(
                "cancellation_reason"
            ),
            "security_semantics": {
                "process_group_supervised": True,
                "minimal_environment": True,
                "network_os_enforced": False,
                "writable_paths_os_enforced": False,
            },
        },
        "selected_run_command_index": selected_index,
        "selected_run_command": selected_command,
        "command_selection_record": state.get(
            "command_selection_record"
        ),
        "pending_action_hash": state.get("pending_action_hash"),
        "approval": {
            "decision": state.get("user_approval"),
            "feedback": state.get("human_feedback"),
            "record": state.get("approval_record"),
        },
        "execution": {
            "log_path": (
                state.get("execution_log_path")
                or state.get("log_path")
            ),
            "result": state.get("execution_result"),
            "evidence": state.get("execution_evidence"),
            "verification": state.get("execution_verification"),
            "verification_sha256": state.get(
                "execution_verification_hash"
            ),
        },
        "errors": {
            "count": len(stage_errors),
            "terminal_count": len(terminal_errors),
            "items": stage_errors,
        },
        "artifacts": {
            "count": len(artifact_records),
            "current_count": current_count,
            "issue_count": len(artifact_records) - current_count,
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
        "file_repair": {
            "attempt_count": state.get(
                "file_repair_attempt_count",
                0,
            ),
            "history": state.get("file_repair_history", []),
            "proposal": state.get("file_repair_proposal"),
            "pending_patch": state.get("pending_patch"),
            "patch_approval": state.get("patch_approval_record"),
            "verification_evidence": state.get(
                "patch_verification_evidence"
            ),
            "verification": state.get(
                "patch_verification_report"
            ),
            "promotion": state.get("patch_promotion_record"),
            "application": state.get(
                "patch_application_record"
            ),
        },
    }

def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """
    在目标目录内写临时文件，再使用 os.replace 原子替换。

    临时文件与目标位于同一文件系统，避免跨设备 rename。
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        with temp_path.open("xb") as file_obj:
            file_obj.write(data)
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

def _guess_media_type(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    if media_type:
        return media_type
    if path.suffix == ".log":
        return "text/plain"
    return "application/octet-stream"

def _artifact_id(run_id: str, relative_path: str) -> str:
    material = f"{run_id}:{relative_path}".encode()
    return "artifact_" + hashlib.sha256(material).hexdigest()[:20]

def build_artifact_record(
    *,
    state: dict[str, Any],
    path: Path,
    producer_node: str,
    media_type: str | None = None,
) -> ArtifactRecord:
    """为已经完整写入磁盘的文件生成元数据。"""

    run_root = require_run_root(state)
    resolved_path = path.resolve()
    if run_root not in resolved_path.parents:
        raise ValueError("不能登记当前 run 之外的 Artifact")
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Artifact 文件不存在：{resolved_path}")

    relative_path = resolved_path.relative_to(run_root).as_posix()
    layer = relative_path.split("/", 1)[0]
    if layer not in ARTIFACT_LAYERS:
        raise ValueError(f"未知 Artifact layer：{layer}")

    run_id = str(state.get("run_id") or "")
    if not run_id:
        raise ValueError("登记 Artifact 时缺少 run_id")

    return ArtifactRecord(
        artifact_id=_artifact_id(run_id, relative_path),
        run_id=run_id,
        layer=layer,
        relative_path=relative_path,
        absolute_path=str(resolved_path),
        media_type=media_type or _guess_media_type(resolved_path),
        sha256=sha256_file(resolved_path),
        size_bytes=resolved_path.stat().st_size,
        producer_node=producer_node,
        created_at=utc_now(),
    )

def write_bytes_artifact(
    *,
    state: dict[str, Any],
    relative_path: str,
    data: bytes,
    producer_node: str,
    media_type: str | None = None,
    redactor: SecretRedactor | None = None,
) -> tuple[Path, ArtifactRecord]:
    """原子写入并立即生成 ArtifactRecord。

    Phase 41: 如果 redactor 非空且 data 包含已知 Secret bytes，fail closed。
    """

    if redactor is not None and redactor.contains_secret_bytes(data):
        raise ValueError(
            "Artifact payload contains protected secret material"
        )
    path = resolve_artifact_path(state, relative_path)
    _atomic_write_bytes(path, data)
    record = build_artifact_record(
        state=state,
        path=path,
        producer_node=producer_node,
        media_type=media_type,
    )
    return path, record

def write_text_artifact(
    *,
    state: dict[str, Any],
    relative_path: str,
    text: str,
    producer_node: str,
    media_type: str = "text/plain",
    redactor: SecretRedactor | None = None,
) -> tuple[Path, ArtifactRecord]:
    """Phase 41: 如果 redactor 非空，先脱敏再写入。"""
    if redactor is not None:
        safe_text = redactor.redact_text(text)
    else:
        safe_text = text
    return write_bytes_artifact(
        state=state,
        relative_path=relative_path,
        data=safe_text.encode("utf-8"),
        producer_node=producer_node,
        media_type=media_type,
        redactor=redactor,
    )

def write_json_artifact(
    *,
    state: dict[str, Any],
    relative_path: str,
    payload: Any,
    producer_node: str,
    redactor: SecretRedactor | None = None,
) -> tuple[Path, ArtifactRecord]:
    """Phase 41: 如果 redactor 非空，先对 payload 做对象级脱敏。"""
    if redactor is not None:
        safe_payload = redactor.redact_object(payload)
    else:
        safe_payload = payload
    text = json.dumps(
        safe_payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    ) + "\n"
    return write_text_artifact(
        state=state,
        relative_path=relative_path,
        text=text,
        producer_node=producer_node,
        media_type="application/json",
        redactor=redactor,
    )

def register_existing_artifact(
    *,
    state: dict[str, Any],
    path: str | Path,
    producer_node: str,
    media_type: str | None = None,
) -> ArtifactRecord:
    """
    登记由已有工具生成的文件。

    例如 patch_tools 一次生成 patch.diff 和 patch_bundle.json，
    节点无需复制文件，只需在生成后登记。
    """

    return build_artifact_record(
        state=state,
        path=Path(path),
        producer_node=producer_node,
        media_type=media_type,
    )

def merge_artifact_records(
    existing: list[dict[str, Any]],
    new_records: list[ArtifactRecord | dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    按 relative_path upsert。

    LangGraph 从 interrupt 恢复时会重新执行节点开头。固定路径 Artifact
    不能因此在 state 中无限重复。
    """

    ordered_paths: list[str] = []
    by_path: dict[str, dict[str, Any]] = {}

    for raw_record in [*existing, *new_records]:
        record = ArtifactRecord.model_validate(raw_record).model_dump()
        relative_path = record["relative_path"]
        if relative_path not in by_path:
            ordered_paths.append(relative_path)
        by_path[relative_path] = record

    return [by_path[path] for path in ordered_paths]

def artifact_state_update(
    state: dict[str, Any],
    records: list[ArtifactRecord | dict[str, Any]],
) -> dict[str, Any]:
    """同时维护新 artifact_records 和兼容字段 output_files。"""

    merged_records = merge_artifact_records(
        list(state.get("artifact_records", [])),
        records,
    )

    output_files: list[str] = []
    seen: set[str] = set()
    for path in [
        *state.get("output_files", []),
        *[record["absolute_path"] for record in merged_records],
    ]:
        if path not in seen:
            seen.add(path)
            output_files.append(path)

    return {
        "artifact_records": merged_records,
        "output_files": output_files,
    }

def inspect_artifact_records(
    state: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """
    在生成 Artifact Index 前重新检查路径和 hash。

    不直接抛出第一个错误，而是收集全部 issue，使失败 Manifest 仍能生成。
    """

    run_root = require_run_root(state)
    inspected: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []

    for raw_record in state.get("artifact_records", []):
        try:
            record = ArtifactRecord.model_validate(raw_record)
        except ValidationError as exc:
            issues.append(
                {
                    "code": "INVALID_ARTIFACT_RECORD",
                    "message": str(exc),
                }
            )
            continue

        path = Path(record.absolute_path).resolve()
        status = "current"
        detail = ""

        if path == run_root or run_root not in path.parents:
            status = "outside_run"
            detail = "Artifact path is outside current run"
        elif not path.is_file():
            status = "missing"
            detail = "Artifact file does not exist"
        else:
            current_hash = sha256_file(path)
            if current_hash != record.sha256:
                status = "hash_mismatch"
                detail = (
                    f"recorded={record.sha256}, current={current_hash}"
                )

        inspected.append(
            {
                **record.model_dump(),
                "integrity_status": status,
                "integrity_detail": detail,
            }
        )

        if status != "current":
            issues.append(
                {
                    "code": f"ARTIFACT_{status.upper()}",
                    "message": (
                        f"{record.relative_path}: {detail or status}"
                    ),
                }
            )

    return inspected, issues
