# tests/test_rerun_command_template.py
from __future__ import annotations

import shlex

import pytest

from app.rerun.command_template import (
    build_command_template,
    resolve_command_template,
)
from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
)
from app.rerun.schemas import RerunArgumentEdit
from app.workspace.schemas import (
    ExternalDataReference,
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _workspace() -> WorkspaceManifest:
    return WorkspaceManifest(
        manifest_version="phase39-v2",
        manifest_id="wm-parent",
        manifest_hash="a" * 64,
        job_id="job-parent",
        run_id="run-parent",
        generation=2,
        source_host_id="host-a",
        entries=[
            WorkspaceBlobEntry(
                logical_path="source/paper.pdf",
                role="paper",
                object_key="workspace/paper",
                sha256="b" * 64,
                size_bytes=10,
            ),
            WorkspaceBlobEntry(
                logical_path="capsule/repository.bundle",
                role="repository_bundle",
                object_key="workspace/repository",
                sha256="c" * 64,
                size_bytes=20,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="d" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        external_data=[
            ExternalDataReference(
                name="NTU60",
                uri="file:///datasets/ntu60",
                fingerprint="ntu60-v1",
                required_worker_label="dataset:ntu60",
            )
        ],
        portable=False,
        blocked_reasons=["blob_store_is_host_local"],
        source_paths=None,
        materialization_mode="blob_entries",
        created_at="2026-08-09T00:00:00+00:00",
    )


def _build(command: str, edits: list[RerunArgumentEdit]):
    return build_command_template(
        selected_action={
            "command": command,
            "cwd": "/parent/repository/modules",
            "source": "readme",
            "risk_level": "high",
        },
        run_manifest={
            "repo_path": "/parent/repository",
            "run_dir": "/parent/run",
        },
        workspace=_workspace(),
        edits=edits,
        max_command_chars=8192,
        max_argv_items=256,
    )


def test_build_and_resolve_template_changes_only_expected_option(
    tmp_path,
) -> None:
    template = _build(
        (
            "python /parent/repository/train.py "
            "--dataset=/datasets/ntu60/train "
            "--output /parent/run/results "
            "--epochs 50 --batch-size=8"
        ),
        [
            RerunArgumentEdit(
                option="--epochs",
                operation="set",
                expected_old_value="50",
                value="100",
            )
        ],
    )
    repo = tmp_path / "child-repository"
    child_run = tmp_path / "child-run"
    dataset = tmp_path / "datasets" / "ntu60"
    repo.mkdir()
    child_run.mkdir()
    dataset.mkdir(parents=True)

    resolved = resolve_command_template(
        template=template,
        repo_path=str(repo),
        run_dir=str(child_run),
        dataset_mounts={"dataset:ntu60": str(dataset)},
    )
    argv = shlex.split(resolved["command"])
    assert argv == [
        "python",
        str(repo / "train.py"),
        "--dataset",
        str(dataset / "train"),
        "--output",
        str(child_run / "results"),
        "--epochs",
        "100",
        "--batch-size",
        "8",
    ]
    assert resolved["cwd"] == str(repo / "modules")
    assert resolved["source"] == "config"
    assert resolved["risk_level"] == "high"


def test_remove_existing_flag() -> None:
    template = _build(
        "python train.py --amp --epochs 50",
        [
            RerunArgumentEdit(
                option="--amp",
                operation="remove",
                expected_old_value=None,
            )
        ],
    )
    literal_values = [
        item.value
        for item in template.argv
        if item.kind == "literal"
    ]
    assert "--amp" not in literal_values


@pytest.mark.parametrize(
    "command",
    [
        "python train.py | tee output.log --epochs 50",
        "python train.py > output.log --epochs 50",
        "TOKEN=secret python train.py --epochs 50",
        "python train.py --token secret --epochs 50",
        "python /unrelated/train.py --epochs 50",
    ],
)
def test_rejects_unsafe_parent_command(command: str) -> None:
    with pytest.raises(RerunCommandRejectedError):
        _build(
            command,
            [
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                )
            ],
        )


def test_rejects_stale_expected_old_value() -> None:
    with pytest.raises(RerunConflictError, match="expected_old_value"):
        _build(
            "python train.py --epochs 50",
            [
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="40",
                    value="100",
                )
            ],
        )


def test_rejects_new_absolute_path() -> None:
    with pytest.raises(RerunCommandRejectedError):
        _build(
            "python train.py --output old --epochs 50",
            [
                RerunArgumentEdit(
                    option="--output",
                    operation="set",
                    expected_old_value="old",
                    value="/host/private/output",
                )
            ],
        )
