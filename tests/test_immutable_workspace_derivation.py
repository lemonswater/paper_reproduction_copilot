# tests/test_immutable_workspace_derivation.py
from __future__ import annotations

import hashlib

import pytest

from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.repository import (
    canonical_json_bytes,
    validate_manifest_hash,
    workspace_manifest_hash,
)
from app.workspace.schemas import (
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
    WorkspaceSourcePaths,
)
from app.workspace.snapshot import WorkspaceSnapshotter


class FakeLocalBlobStore:
    sharing_scope = "host-local"

    def ensure_ready(self) -> None:
        return None


def _entries() -> list[WorkspaceBlobEntry]:
    return [
        WorkspaceBlobEntry(
            logical_path="source/paper.pdf",
            role="paper",
            object_key="workspace/paper",
            sha256="a" * 64,
            size_bytes=10,
        ),
        WorkspaceBlobEntry(
            logical_path="capsule/repository.bundle",
            role="repository_bundle",
            object_key="workspace/repository",
            sha256="b" * 64,
            size_bytes=20,
        ),
        WorkspaceBlobEntry(
            logical_path="run/reports/final_report.md",
            role="run_artifact",
            object_key="workspace/report",
            sha256="c" * 64,
            size_bytes=30,
        ),
    ]


def _parent() -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_version="phase39-v2",
        manifest_id="wm-pending",
        manifest_hash="0" * 64,
        job_id="job-parent",
        run_id="run-parent",
        generation=2,
        source_host_id="host-a",
        entries=_entries(),
        repository=RepositoryIdentity(
            commit_sha="d" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        portable=False,
        blocked_reasons=["blob_store_is_host_local"],
        source_paths=WorkspaceSourcePaths(
            run_dir="/old/run",
            repo_path="/old/repo",
            paper_path="/old/paper.pdf",
        ),
        materialization_mode="auto",
        created_at="2026-08-09T00:00:00+00:00",
    )
    digest = workspace_manifest_hash(draft)
    return draft.model_copy(
        update={
            "manifest_id": f"wm_{digest[:32]}",
            "manifest_hash": digest,
        }
    )


def test_derive_reuses_only_immutable_input_entries() -> None:
    snapshotter = WorkspaceSnapshotter(
        blob_store=FakeLocalBlobStore()
    )
    parent = _parent()
    child = snapshotter.derive_initial(
        job_id="job-child",
        run_id="run-child",
        parent=parent,
        source_host_id="host-a",
        external_data=[],
    )
    validate_manifest_hash(child)
    assert child.generation == 0
    assert child.parent_manifest_id == parent.manifest_id
    assert child.materialization_mode == "blob_entries"
    assert child.portable is False
    assert child.source_paths is None
    assert {item.role for item in child.entries} == {
        "paper",
        "repository_bundle",
    }
    assert {item.object_key for item in child.entries} == {
        "workspace/paper",
        "workspace/repository",
    }


def test_phase26_hash_ignores_new_default_field() -> None:
    payload = {
        "manifest_version": "phase26-v1",
        "manifest_id": "wm-old",
        "manifest_hash": "",
        "job_id": "job-old",
        "run_id": "run-old",
        "generation": 0,
        "parent_manifest_id": None,
        "source_host_id": "host-a",
        "source_worker_session_id": None,
        "entries": [item.model_dump(mode="json") for item in _entries()[:2]],
        "repository": {
            "commit_sha": "d" * 40,
            "branch": "main",
            "clean": True,
            "bundle_logical_path": "capsule/repository.bundle",
            "has_submodules": False,
            "has_lfs": False,
        },
        "external_data": [],
        "portable": False,
        "blocked_reasons": ["blob_store_is_host_local"],
        "source_paths": {
            "run_dir": None,
            "repo_path": "/old/repo",
            "paper_path": "/old/paper.pdf",
            "log_path": None,
        },
        "created_at": "2026-08-01T00:00:00+00:00",
    }
    historical = dict(payload)
    historical.pop("manifest_hash")
    historical.pop("manifest_id")
    historical.pop("created_at")
    digest = hashlib.sha256(
        canonical_json_bytes(historical)
    ).hexdigest()
    payload["manifest_hash"] = digest

    loaded = WorkspaceManifest.model_validate(payload)
    assert loaded.materialization_mode == "auto"
    validate_manifest_hash(loaded)


def test_phase39_hash_binds_materialization_mode() -> None:
    parent = _parent()
    changed = parent.model_copy(
        update={"materialization_mode": "host_paths"}
    )
    with pytest.raises(WorkspaceIntegrityError, match="hash"):
        validate_manifest_hash(changed)
