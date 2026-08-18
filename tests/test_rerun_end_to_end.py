# tests/test_rerun_end_to_end.py
"""Phase 39 端到端控制面闭环测试。

不调用真实 LLM 或训练程序，使用 Mock 验证从 create -> submit -> derived job 的完整流程。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.interaction.schemas import ArtifactView
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


def _parent_evidence() -> VerifiedRunEvidence:
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
            WorkspaceBlobEntry(
                logical_path="execution/metrics.json",
                role="run_artifact",
                object_key="workspace/output",
                sha256="d" * 64,
                size_bytes=30,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="e" * 40,
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
        sha256="f" * 64,
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
                "command": "python train.py --epochs 50 --batch-size 8",
                "cwd": "/parent/repo",
                "source": "readme",
                "risk_level": "high",
            },
        },
    )


def _build_service(tmp_path):
    """Build a RerunService with mocked reader and job_service."""
    evidence = _parent_evidence()
    reader = Mock()
    reader.read.return_value = evidence

    child_job = SimpleNamespace(
        job_id="job-child-001",
        run_id="run-child-001",
        thread_id="rerun-rerun_abc123",
        status="queued",
        workspace_manifest_id="wm-child-001",
    )
    jobs = Mock()
    jobs.submit.return_value = (child_job, True)
    jobs.get.return_value = child_job

    repository = SqliteRerunRepository(
        tmp_path / "rerun_e2e.sqlite",
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
            execution_policy_hash="a" * 64,
            execution_backend="local",
        ),
    )
    return service, reader, jobs, evidence, child_job


def test_e2e_create_submit_derives_new_job(tmp_path):
    """Full control plane: create -> submit -> verify derived job."""
    service, reader, jobs, evidence, child_job = _build_service(tmp_path)

    # Step 1: Create proposal
    proposal_record, created = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="f" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                ),
            ],
        ),
        idempotency_key="e2e-create-001",
    )
    assert created is True
    assert proposal_record.status == "pending"
    proposal = proposal_record.proposal

    # Step 2: Submit proposal
    submit_record, child, child_created = service.submit_proposal(
        proposal_id=proposal.proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=proposal.proposal_hash,
            expected_version=proposal_record.version,
        ),
        idempotency_key="e2e-submit-001",
    )
    assert child_created is True
    assert submit_record.status == "submitted"
    assert submit_record.child_job_id == child_job.job_id

    # Step 3: Verify child job has different identity from parent
    assert child.job_id != evidence.job.job_id
    assert child.run_id != evidence.job.run_id
    assert child.thread_id != "rerun-thread-parent"

    # Step 4: Verify derived job request was constructed correctly
    kwargs = jobs.submit.call_args.kwargs
    request = kwargs["request"]

    # Derived run input must carry proposal identity
    assert request.derived_run is not None
    assert request.derived_run.proposal_id == proposal.proposal_id
    assert request.derived_run.proposal_hash == proposal.proposal_hash

    # Command template must reflect the edited value
    argv = request.derived_run.command_template.argv
    epochs_arg = next(a for a in argv if a.value == "100")
    assert epochs_arg.value == "100"

    # Derived job must not carry parent paths or resources
    assert request.paper_path is None
    assert request.repo_path is None
    assert request.paper_resource is None
    assert request.repo_resource is None

    # Thread ID must be derived from proposal, not parent
    assert kwargs["thread_id"] == f"rerun-{proposal.proposal_id}"

    # Idempotency key must be anchored to proposal ID
    assert kwargs["idempotency_key"] == f"rerun-submit:{proposal.proposal_id}"


def test_e2e_submit_is_idempotent(tmp_path):
    """Replaying submit with same idempotency key returns same child."""
    service, _reader, jobs, _evidence, child_job = _build_service(tmp_path)

    proposal_record, _ = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="f" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                ),
            ],
        ),
        idempotency_key="e2e-create-002",
    )
    proposal = proposal_record.proposal

    # First submit
    _, child_first, created_first = service.submit_proposal(
        proposal_id=proposal.proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=proposal.proposal_hash,
            expected_version=proposal_record.version,
        ),
        idempotency_key="e2e-submit-002",
    )
    assert created_first is True

    # Replay submit with same idempotency key
    _, child_replay, created_replay = service.submit_proposal(
        proposal_id=proposal.proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=proposal.proposal_hash,
            expected_version=proposal_record.version + 1,
        ),
        idempotency_key="e2e-submit-002",
    )
    assert created_replay is False
    assert child_first.job_id == child_replay.job_id
    # Job service should only be called once
    assert jobs.submit.call_count == 1


def test_e2e_command_template_preserves_unedited_options(tmp_path):
    """Unedited options from parent command must be preserved."""
    service, _reader, _jobs, _evidence, _child = _build_service(tmp_path)

    proposal_record, _ = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="f" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--batch-size",
                    operation="set",
                    expected_old_value="8",
                    value="16",
                ),
            ],
        ),
        idempotency_key="e2e-create-003",
    )
    template = proposal_record.proposal.command_template

    # Parent command: python train.py --epochs 50 --batch-size 8
    # After edit: python train.py --epochs 50 --batch-size 16
    arg_values = [a.value for a in template.argv if a.value]
    assert "16" in arg_values
    assert "50" in arg_values


def test_e2e_derived_job_carries_dataset_refs(tmp_path):
    """Dataset refs from parent workspace must be deep-copied to child."""
    service, _reader, jobs, evidence, _child = _build_service(tmp_path)

    # Add external data to the parent workspace
    from app.workspace.schemas import ExternalDataReference

    evidence.workspace.external_data = [
        ExternalDataReference(
            name="ntu_dataset",
            uri="/data/private/ntu",
            fingerprint="sha256:abc",
            required_worker_label="gpu",
        ),
    ]

    proposal_record, _ = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="f" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                ),
            ],
        ),
        idempotency_key="e2e-create-004",
    )
    service.submit_proposal(
        proposal_id=proposal_record.proposal.proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=proposal_record.proposal.proposal_hash,
            expected_version=proposal_record.version,
        ),
        idempotency_key="e2e-submit-004",
    )

    kwargs = jobs.submit.call_args.kwargs
    request = kwargs["request"]
    assert len(request.dataset_refs) == 1
    assert request.dataset_refs[0].name == "ntu_dataset"
