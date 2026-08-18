from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas import CancellationRequest
from app.workspace.paths import require_managed_run_root


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_control_dir(run_dir: str | Path) -> Path:
    run_root = require_managed_run_root(run_dir)

    control_dir = (run_root / "execution" / "control").resolve()
    if run_root not in control_dir.parents:
        raise ValueError("control 目录逃逸当前 run")
    control_dir.mkdir(parents=True, exist_ok=True)
    return control_dir


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n"
    ).encode("utf-8")

    try:
        with temp_path.open("xb") as file_obj:
            file_obj.write(data)
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def runtime_record_path(
    run_dir: str | Path,
    execution_id: str,
) -> Path:
    if not execution_id or Path(execution_id).name != execution_id:
        raise ValueError(f"无效 execution_id：{execution_id!r}")
    return require_control_dir(run_dir) / (
        f"{execution_id}.runtime.json"
    )


def cancel_request_path(
    run_dir: str | Path,
    execution_id: str,
) -> Path:
    if not execution_id or Path(execution_id).name != execution_id:
        raise ValueError(f"无效 execution_id：{execution_id!r}")
    return require_control_dir(run_dir) / (
        f"{execution_id}.cancel.json"
    )


def write_runtime_record(
    *,
    run_dir: str | Path,
    execution_id: str,
    payload: dict[str, Any],
) -> Path:
    path = runtime_record_path(run_dir, execution_id)
    atomic_write_json(path, payload)
    return path


def read_cancel_request(
    *,
    run_dir: str | Path,
    execution_id: str,
) -> CancellationRequest | None:
    path = cancel_request_path(run_dir, execution_id)
    if not path.is_file():
        return None
    return CancellationRequest.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def list_runtime_records(
    run_dir: str | Path,
) -> list[dict[str, Any]]:
    control_dir = require_control_dir(run_dir)
    records: list[dict[str, Any]] = []
    for path in sorted(control_dir.glob("*.runtime.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        payload["runtime_record_path"] = str(path)
        records.append(payload)
    return records


def request_run_cancellation(
    *,
    run_dir: str | Path,
    reason: str,
    requested_by: str = "cli",
) -> CancellationRequest:
    """
    找到当前 run 唯一的 running/starting execution 并写取消请求。

    如果存在多个活动记录，fail closed，要求人工先诊断，不能猜 PID。
    """

    active = [
        item
        for item in list_runtime_records(run_dir)
        if item.get("status") in {"starting", "running", "terminating"}
    ]
    if not active:
        raise ValueError("当前 run 没有活动中的受监管进程")
    if len(active) != 1:
        raise ValueError(
            "当前 run 存在多个活动进程记录，拒绝猜测取消目标"
        )

    execution_id = str(active[0].get("execution_id") or "")
    if not execution_id:
        raise ValueError("活动进程记录缺少 execution_id")

    request = CancellationRequest(
        execution_id=execution_id,
        requested_at=utc_now(),
        requested_by=requested_by[:100],
        reason=(reason.strip() or "user requested cancellation")[:500],
    )
    atomic_write_json(
        cancel_request_path(run_dir, execution_id),
        request.model_dump(),
    )
    return request