from __future__ import annotations

"""Phase 26 §48: Materializer 完整性测试。"""

from pathlib import Path

import pytest

from app.config import settings
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.workspace.errors import (
    WorkspaceIntegrityError,
)
from app.workspace.materializer import (
    WorkspaceMaterializer,
)
from app.workspace.repository import (
    workspace_manifest_hash,
)
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
)
from app.workspace.snapshot import (
    WorkspaceSnapshotter,
)
from tests.test_repo_capsule import _clean_repo


class SharedLocalBlobStore(LocalBlobStore):
    """测试中用两个不同 workspace root 模拟共享对象存储。"""

    sharing_scope = "shared"


def _worker(root: Path) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id="worker-b",
        worker_session_id="session-b",
        host_id="host-b",
        pool="default",
        workspace_root=str(root.resolve()),
        capabilities=WorkerCapabilities(
            execution_profile_ids=["local"],
            execution_backends=["local"],
            execution_policy_hashes={
                "local": "a" * 64
            },
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            workspace_free_bytes=100 * 1024**3,
        ),
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        execution_profile_id="local",
        execution_policy_hash="a" * 64,
        execution_backend="local",
    )


def _portable_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(
        settings,
        "workspace_staging_root",
        staging,
    )
    monkeypatch.setattr(
        settings,
        "workspace_max_file_bytes",
        1024**3,
    )
    monkeypatch.setattr(
        settings,
        "workspace_max_total_bytes",
        2 * 1024**3,
    )

    repo = _clean_repo(tmp_path)
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\nfixture\n")
    blob = SharedLocalBlobStore(
        tmp_path / "blobs"
    )
    snapshotter = WorkspaceSnapshotter(
        blob_store=blob
    )
    manifest = snapshotter.snapshot_initial(
        job_id="job-test",
        run_id="run-test",
        paper_path=str(paper),
        repo_path=str(repo),
        log_path=None,
        source_host_id="host-a",
        external_data=[],
    )
    assert manifest.portable is True
    return manifest, blob


def test_materialize_verifies_repo_and_paper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, blob = _portable_manifest(
        tmp_path, monkeypatch
    )
    worker_root = (
        tmp_path / "host-b-workspaces"
    )
    monkeypatch.setattr(
        settings,
        "worker_workspace_root",
        worker_root,
    )

    materializer = WorkspaceMaterializer(
        blob_store=blob
    )
    binding = materializer.planned_binding(
        worker=_worker(worker_root),
        manifest=manifest,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-1",
    )
    ready = materializer.materialize(
        manifest=manifest,
        binding=binding,
    )

    assert ready.status == "ready"
    assert Path(
        ready.paper_path
    ).read_bytes().startswith(b"%PDF")
    assert (
        Path(ready.repo_path) / "train.py"
    ).is_file()
    assert Path(
        ready.run_dir, "analysis"
    ).is_dir()


def test_corrupted_blob_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, blob = _portable_manifest(
        tmp_path, monkeypatch
    )
    paper_entry = next(
        item
        for item in manifest.entries
        if item.role == "paper"
    )
    blob_path = blob._path(  # noqa: SLF001
        paper_entry.object_key
    )
    blob_path.write_bytes(
        b"X" * paper_entry.size_bytes
    )

    worker_root = (
        tmp_path / "host-b-workspaces"
    )
    monkeypatch.setattr(
        settings,
        "worker_workspace_root",
        worker_root,
    )
    materializer = WorkspaceMaterializer(
        blob_store=blob
    )
    binding = materializer.planned_binding(
        worker=_worker(worker_root),
        manifest=manifest,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-1",
    )
    with pytest.raises(WorkspaceIntegrityError):
        materializer.materialize(
            manifest=manifest,
            binding=binding,
        )


def test_path_traversal_entry_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, blob = _portable_manifest(
        tmp_path, monkeypatch
    )
    first = manifest.entries[0].model_copy(
        update={"logical_path": "../escape"}
    )
    changed = manifest.model_copy(
        update={
            "entries": [
                first,
                *manifest.entries[1:],
            ]
        }
    )
    changed = changed.model_copy(
        update={
            "manifest_hash": workspace_manifest_hash(
                changed
            )
        }
    )

    worker_root = (
        tmp_path / "host-b-workspaces"
    )
    monkeypatch.setattr(
        settings,
        "worker_workspace_root",
        worker_root,
    )
    materializer = WorkspaceMaterializer(
        blob_store=blob
    )
    binding = materializer.planned_binding(
        worker=_worker(worker_root),
        manifest=changed,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-1",
    )
    with pytest.raises(WorkspaceIntegrityError):
        materializer.materialize(
            manifest=changed,
            binding=binding,
        )
