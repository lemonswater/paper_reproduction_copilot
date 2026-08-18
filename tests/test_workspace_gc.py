from __future__ import annotations

"""Phase 26 §54: 本地 Workspace GC 测试。

验证 GC 默认 dry-run，且只删除 marker 匹配的 released epoch 目录。
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.config import settings
from app.workspace.gc import WorkspaceGarbageCollector
from tests.test_workspace_rebind import _binding


class FakeGcStore:
    def __init__(self, binding):
        self.binding = binding
        self.marked: list[str] = []

    def list_workspace_gc_candidates(
        self,
        *,
        host_id: str,
        older_than: str,
        limit: int,
    ):
        del older_than, limit
        return (
            [self.binding]
            if self.binding.host_id == host_id
            else []
        )

    def mark_workspace_garbage_collected(
        self,
        *,
        assignment_id: str,
        assignment_token: str,
        host_id: str,
    ):
        assert assignment_token == self.binding.assignment_token
        assert host_id == self.binding.host_id
        self.marked.append(assignment_id)
        return self.binding.model_copy(
            update={
                "status": "garbage_collected",
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )


def test_gc_is_dry_run_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "worker"
    monkeypatch.setattr(
        settings, "worker_workspace_root", root
    )
    monkeypatch.setattr(
        settings, "workspace_gc_min_age_seconds", 0
    )
    binding = _binding(host="host-a", epoch=1).model_copy(
        update={
            "workspace_root": str(
                root / "jobs/job-test/epochs/00000001"
            ),
            "status": "released",
        }
    )
    epoch = Path(binding.workspace_root)
    epoch.mkdir(parents=True)
    (epoch / ".workspace-binding.json").write_text(
        binding.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    store = FakeGcStore(binding)
    report = WorkspaceGarbageCollector(
        store=store,
        host_id="host-a",
    ).collect(dry_run=True)

    assert report["removed_or_planned"] == [
        binding.assignment_id
    ]
    assert epoch.exists()
    assert store.marked == []


def test_gc_deletes_only_matching_released_epoch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "worker"
    monkeypatch.setattr(
        settings, "worker_workspace_root", root
    )
    monkeypatch.setattr(
        settings, "workspace_gc_min_age_seconds", 0
    )
    binding = _binding(host="host-a", epoch=1).model_copy(
        update={
            "workspace_root": str(
                root / "jobs/job-test/epochs/00000001"
            ),
            "status": "released",
        }
    )
    epoch = Path(binding.workspace_root)
    epoch.mkdir(parents=True)
    (epoch / ".workspace-binding.json").write_text(
        binding.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    store = FakeGcStore(binding)
    WorkspaceGarbageCollector(
        store=store,
        host_id="host-a",
    ).collect(dry_run=False)

    assert not epoch.exists()
    assert store.marked == [binding.assignment_id]
