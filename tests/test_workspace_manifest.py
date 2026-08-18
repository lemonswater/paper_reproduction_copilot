from __future__ import annotations

"""Phase 26 §46: Manifest hash 测试。"""

from datetime import datetime, timezone

import pytest

from app.workspace.errors import (
    WorkspaceIntegrityError,
)
from app.workspace.repository import (
    validate_manifest_hash,
    workspace_manifest_hash,
)
from app.workspace.schemas import (
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _manifest() -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_id="wm-test",
        manifest_hash="",
        job_id="job-test",
        run_id="run-test",
        generation=0,
        source_host_id="host-a",
        entries=[
            WorkspaceBlobEntry(
                logical_path="source/paper.pdf",
                role="paper",
                object_key=(
                    "workspace/sha256/aa/" + "a" * 64
                ),
                sha256="a" * 64,
                size_bytes=10,
                media_type="application/pdf",
            ),
            WorkspaceBlobEntry(
                logical_path="capsule/repository.bundle",
                role="repository_bundle",
                object_key=(
                    "workspace/sha256/bb/" + "b" * 64
                ),
                sha256="b" * 64,
                size_bytes=20,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="c" * 40,
            branch="main",
            clean=True,
            bundle_logical_path=(
                "capsule/repository.bundle"
            ),
        ),
        portable=True,
        created_at=datetime.now(
            timezone.utc
        ).isoformat(),
    )
    return draft.model_copy(
        update={
            "manifest_hash": workspace_manifest_hash(
                draft
            )
        }
    )


def test_manifest_hash_is_canonical() -> None:
    manifest = _manifest()
    validate_manifest_hash(manifest)
    dumped = manifest.model_dump()
    reordered = dict(
        reversed(list(dumped.items()))
    )
    assert (
        workspace_manifest_hash(reordered)
        == manifest.manifest_hash
    )


def test_manifest_tampering_is_detected() -> None:
    manifest = _manifest()
    changed_entry = manifest.entries[
        0
    ].model_copy(update={"size_bytes": 11})
    tampered = manifest.model_copy(
        update={
            "entries": [
                changed_entry,
                manifest.entries[1],
            ]
        }
    )
    with pytest.raises(
        WorkspaceIntegrityError
    ):
        validate_manifest_hash(tampered)


def test_non_portable_manifest_requires_source_paths() -> None:
    from app.workspace.schemas import (
        WorkspaceSourcePaths,
    )

    draft = WorkspaceManifest(
        manifest_id="wm-nonportable",
        manifest_hash="",
        job_id="job-np",
        run_id="run-np",
        generation=0,
        source_host_id="host-a",
        entries=[],
        repository=RepositoryIdentity(
            commit_sha="d" * 40,
            branch="main",
            clean=False,
            bundle_logical_path=None,
        ),
        portable=False,
        blocked_reasons=["dirty_repository"],
        source_paths=WorkspaceSourcePaths(
            repo_path="/data/repo",
            paper_path="/data/paper.pdf",
        ),
        created_at=datetime.now(
            timezone.utc
        ).isoformat(),
    )
    finalized = draft.model_copy(
        update={
            "manifest_hash": workspace_manifest_hash(
                draft
            )
        }
    )
    validate_manifest_hash(finalized)
