# tests/test_rerun_service.py
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.interaction.schemas import ArtifactView
from app.rerun.errors import RerunConflictError
from app.rerun.repository import SqliteRerunRepository
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunProposalCreateRequest,
    RerunProposalSubmitRequest,
)
from app.rerun.service import RerunService
from app.run_evidence.schemas import VerifiedRunEvidence
from app.workspace.schemas import (
    JobRequirements,
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _evidence() -> VerifiedRunEvidence:
    workspace = WorkspaceManifest(
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
        portable=False,
        blocked_reasons=["blob_store_is_host_local"],
        materialization_mode="blob_entries",
        created_at="2026-08-09T00:00:00+00:00",
    )
    job = SimpleNamespace(
        job_id="job-parent",
        run_id="run-parent",
        version=4,
        request=SimpleNamespace(
            experiment_goal="复现 main result",
            execution_profile_id="cpu-local",
        ),
    )
    artifact = ArtifactView(
        artifact_id="artifact-manifest",
        run_id="run-parent",
        layer="reports",
        relative_path="reports/run_manifest.json",
        media_type="application/json",
        sha256="e" * 64,
        size_bytes=100,
        producer_node="run_manifest",
        created_at="2026-08-09T00:00:00+00:00",
    )
    return VerifiedRunEvidence(
        job=job,
        workspace=workspace,
        artifacts=(artifact,),
        run_manifest_artifact=artifact,
        run_manifest={
            "job_id": "job-parent",
            "run_id": "run-parent",
            "repo_path": "/parent/repo",
            "run_dir": "/parent/run",
            "selected_run_command": {
                "command": "python train.py --epochs 50",
                "cwd": "/parent/repo",
                "source": "readme",
                "risk_level": "high",
            },
        },
    )


def _service(tmp_path):
    evidence = _evidence()
    reader = Mock()
    reader.read.return_value = evidence
    jobs = Mock()
    jobs.submit.return_value = (
        SimpleNamespace(
            job_id="job-child",
            thread_id="rerun-thread",
            status="queued",
        ),
        True,
    )
    repository = SqliteRerunRepository(
        tmp_path / "rerun.sqlite",
        clock=lambda: "2026-08-09T01:00:00+00:00",
    )
    service = RerunService(
        repository=repository,
        evidence_reader=reader,
        job_service=jobs,
        comparison_reader=None,
        proposal_ttl_seconds=3600,
        max_command_chars=8192,
        max_argv_items=256,
        max_edits=16,
        clock=lambda: "2026-08-09T01:00:00+00:00",
        requirements_resolver=lambda profile_id: JobRequirements(
            execution_profile_id=profile_id,
            execution_policy_hash="f" * 64,
            execution_backend="local",
        ),
    )
    return service, reader, jobs, evidence


def test_create_and_submit_builds_derived_job_request(tmp_path) -> None:
    service, reader, jobs, evidence = _service(tmp_path)
    proposal, created = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="e" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                )
            ],
        ),
        idempotency_key="create-1",
    )
    assert created is True
    assert proposal.status == "pending"

    submitted, child, child_created = service.submit_proposal(
        proposal_id=proposal.proposal.proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=proposal.proposal.proposal_hash,
            expected_version=proposal.version,
        ),
        idempotency_key="submit-operation-1",
    )
    assert child_created is True
    assert child.job_id == "job-child"
    assert submitted.status == "submitted"
    assert reader.read.call_count == 2

    kwargs = jobs.submit.call_args.kwargs
    request = kwargs["request"]
    assert request.paper_path is None
    assert request.repo_path is None
    assert request.paper_resource is None
    assert request.repo_resource is None
    assert request.derived_run.proposal_id == proposal.proposal.proposal_id
    assert request.derived_run.command_template.argv[-1].value == "100"
    assert kwargs["idempotency_key"] == (
        f"rerun-submit:{proposal.proposal.proposal_id}"
    )


def test_create_with_wrong_manifest_sha_conflicts(tmp_path) -> None:
    service, _reader, _jobs, _evidence = _service(tmp_path)
    with pytest.raises(RerunConflictError):
        service.create_proposal(
            request=RerunProposalCreateRequest(
                parent_job_id="job-parent",
                expected_parent_job_version=4,
                expected_parent_run_manifest_sha256="0" * 64,
                edits=[
                    RerunArgumentEdit(
                        option="--epochs",
                        operation="set",
                        expected_old_value="50",
                        value="100",
                    )
                ],
            ),
            idempotency_key="create-1",
        )


def test_create_idempotent_replay(tmp_path) -> None:
    service, reader, _jobs, _evidence = _service(tmp_path)
    request = RerunProposalCreateRequest(
        parent_job_id="job-parent",
        expected_parent_job_version=4,
        expected_parent_run_manifest_sha256="e" * 64,
        edits=[
            RerunArgumentEdit(
                option="--epochs",
                operation="set",
                expected_old_value="50",
                value="100",
            )
        ],
    )
    first, first_created = service.create_proposal(
        request=request,
        idempotency_key="create-1",
    )
    second, second_created = service.create_proposal(
        request=request,
        idempotency_key="create-1",
    )
    assert first_created is True
    assert second_created is False
    assert first.proposal.proposal_id == second.proposal.proposal_id
    # Idempotent replay should not call reader again
    assert reader.read.call_count == 1


def test_cancel_proposal(tmp_path) -> None:
    service, _reader, _jobs, _evidence = _service(tmp_path)
    proposal, _ = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="e" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                )
            ],
        ),
        idempotency_key="create-1",
    )
    from app.rerun.schemas import RerunProposalCancelRequest

    cancelled = service.cancel_proposal(
        proposal_id=proposal.proposal.proposal_id,
        request=RerunProposalCancelRequest(
            expected_proposal_hash=proposal.proposal.proposal_hash,
            expected_version=proposal.version,
            reason="not needed",
        ),
    )
    assert cancelled.status == "cancelled"
