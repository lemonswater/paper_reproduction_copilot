from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.job_runtime.ports import JobStore
from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.schemas import WorkspaceBinding

_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _safe_component(value: str, *, field: str) -> str:
    if (
        value in {".", ".."}
        or not _SAFE_PATH_COMPONENT.fullmatch(value)
    ):
        raise WorkspaceIntegrityError(
            f"{field} 不能作为受管目录名：{value!r}"
        )
    return value


def _expected_epoch_root(binding: WorkspaceBinding) -> Path:
    root = settings.worker_workspace_root.resolve()
    job_component = _safe_component(
        binding.job_id,
        field="job_id",
    )
    epoch_component = f"{binding.assignment_epoch:08d}"
    expected = (
        root
        / "jobs"
        / job_component
        / "epochs"
        / epoch_component
    )
    resolved = expected.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise WorkspaceIntegrityError("GC 目标逃逸 worker root")
    return expected


def _reject_symlink_chain(path: Path, root: Path) -> None:
    current = path
    while current != root:
        if current.is_symlink():
            raise WorkspaceIntegrityError(
                f"GC 路径链包含 symlink：{current}"
            )
        if root not in current.parents:
            raise WorkspaceIntegrityError("GC 路径逃逸 worker root")
        current = current.parent


class WorkspaceGarbageCollector:
    def __init__(self, *, store: JobStore, host_id: str):
        self.store = store
        self.host_id = host_id

    def collect(
        self,
        *,
        dry_run: bool,
        limit: int = 100,
    ) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.workspace_gc_min_age_seconds
        )
        candidates = self.store.list_workspace_gc_candidates(
            host_id=self.host_id,
            older_than=cutoff.isoformat(),
            limit=limit,
        )
        removed: list[str] = []
        skipped: list[dict[str, str]] = []

        for binding in candidates:
            expected = _expected_epoch_root(binding)
            declared = Path(binding.workspace_root)
            if declared != expected:
                skipped.append(
                    {
                        "assignment_id": binding.assignment_id,
                        "reason": "workspace_root_mismatch",
                    }
                )
                continue

            _reject_symlink_chain(expected, settings.worker_workspace_root.resolve())
            marker = expected / ".workspace-binding.json"
            if expected.exists():
                if not marker.is_file() or marker.is_symlink():
                    skipped.append(
                        {
                            "assignment_id": binding.assignment_id,
                            "reason": "binding_marker_missing",
                        }
                    )
                    continue
                local = WorkspaceBinding.model_validate_json(
                    marker.read_text(encoding="utf-8")
                )
                if (
                    local.assignment_id != binding.assignment_id
                    or local.assignment_token != binding.assignment_token
                    or local.manifest_hash != binding.manifest_hash
                ):
                    skipped.append(
                        {
                            "assignment_id": binding.assignment_id,
                            "reason": "binding_marker_mismatch",
                        }
                    )
                    continue

            if dry_run:
                removed.append(binding.assignment_id)
                continue

            if expected.exists():
                shutil.rmtree(expected)
            self.store.mark_workspace_garbage_collected(
                assignment_id=binding.assignment_id,
                assignment_token=binding.assignment_token,
                host_id=self.host_id,
            )
            removed.append(binding.assignment_id)

        return {
            "dry_run": dry_run,
            "candidate_count": len(candidates),
            "removed_or_planned": removed,
            "skipped": skipped,
        }
