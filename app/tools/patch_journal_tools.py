from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.config import settings
from app.schemas import PatchApplicationJournal, PatchBundle
from app.tools.repository_lock_tools import repository_lock_key


def patch_journal_path(bundle: PatchBundle) -> Path:
    """同一 repo + patch 在所有 run 中共享一个 journal。"""

    repo_key = repository_lock_key(bundle.repo_path)
    journal_dir = settings.patch_coordination_dir / "journals" / repo_key
    journal_dir.mkdir(parents=True, exist_ok=True)
    return journal_dir / f"{bundle.patch_sha256}.json"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """写临时文件并 fsync，再原子替换目标 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")

    with temp_path.open("wb") as file_obj:
        file_obj.write(encoded)
        file_obj.flush()
        os.fsync(file_obj.fileno())

    os.replace(temp_path, path)
    directory_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def load_patch_journal(
    bundle: PatchBundle,
) -> PatchApplicationJournal | None:
    path = patch_journal_path(bundle)
    if not path.exists():
        return None
    return PatchApplicationJournal.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def write_patch_journal(
    *,
    bundle: PatchBundle,
    owner_run_id: str,
    status: Literal[
        "prepared",
        "applying",
        "applied",
        "blocked",
        "manual_intervention",
    ],
    repository_state: Literal["before", "after", "conflict"],
    recovered: bool = False,
    error: str | None = None,
) -> tuple[PatchApplicationJournal, Path]:
    path = patch_journal_path(bundle)
    previous = load_patch_journal(bundle)
    now = datetime.now(timezone.utc).isoformat()

    journal = PatchApplicationJournal(
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        repo_path=bundle.repo_path,
        base_git_commit=bundle.base_git_commit,
        owner_run_id=owner_run_id,
        status=status,
        files=bundle.files,
        repository_state=repository_state,
        recovered=recovered,
        error=error,
        created_at=previous.created_at if previous else now,
        updated_at=now,
    )
    atomic_write_json(path, journal.model_dump())
    return journal, path