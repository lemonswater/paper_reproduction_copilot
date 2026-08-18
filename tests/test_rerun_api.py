# tests/test_rerun_api.py
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import install_error_handlers
from app.api.rerun_routes import router as rerun_router
from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
    RerunExpiredError,
    RerunIntegrityError,
    RerunNotFoundError,
)
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunCommandTemplate,
    RerunProposal,
    RerunProposalRecord,
    RerunSourceIdentity,
    RerunTemplateArg,
)
from app.rerun.identity import (
    command_template_hash,
    proposal_hash,
    proposal_id_for_hash,
)
from app.rerun.service import RerunService


def _proposal_record(
    *,
    status: str = "pending",
    version: int = 0,
) -> RerunProposalRecord:
    template_draft = RerunCommandTemplate(
        argv=[
            RerunTemplateArg(kind="literal", value="python"),
            RerunTemplateArg(kind="literal", value="train.py"),
            RerunTemplateArg(kind="literal", value="--epochs"),
            RerunTemplateArg(kind="literal", value="100"),
        ],
        cwd_relative=".",
        reason="test rerun",
        parent_command_sha256="a" * 64,
        template_hash="0" * 64,
    )
    template = template_draft.model_copy(
        update={"template_hash": command_template_hash(template_draft)}
    )
    draft = RerunProposal(
        proposal_id="rerun_" + "0" * 24,
        proposal_hash="0" * 64,
        source=RerunSourceIdentity(
            parent_job_id="job-parent",
            parent_run_id="run-parent",
            parent_workspace_manifest_id="wm-parent",
            parent_workspace_manifest_hash="b" * 64,
            parent_workspace_generation=2,
            parent_run_manifest_artifact_id="artifact-manifest",
            parent_run_manifest_sha256="c" * 64,
        ),
        edits=[
            RerunArgumentEdit(
                option="--epochs",
                operation="set",
                expected_old_value="50",
                value="100",
            )
        ],
        command_template=template,
        experiment_goal="rerun test",
        execution_profile_id="cpu-local",
        execution_policy_hash="e" * 64,
        execution_backend="local",
        created_at="2026-08-09T01:00:00+00:00",
        expires_at="2026-08-10T01:00:00+00:00",
    )
    digest = proposal_hash(draft)
    final_proposal = draft.model_copy(
        update={
            "proposal_hash": digest,
            "proposal_id": proposal_id_for_hash(digest),
        }
    )
    return RerunProposalRecord(
        proposal=final_proposal,
        status=status,
        version=version,
        updated_at="2026-08-09T01:00:00+00:00",
    )


def _fake_service() -> Mock:
    service = Mock(spec=RerunService)
    service.repository = Mock()
    service.repository.ping.return_value = True
    record = _proposal_record()
    service.create_proposal.return_value = (record, True)
    service.get_proposal.return_value = record
    service.submit_proposal.return_value = (
        record.model_copy(update={"status": "submitted"}),
        SimpleNamespace(
            job_id="job-child",
            thread_id="rerun-thread",
            status="queued",
        ),
        True,
    )
    service.cancel_proposal.return_value = record.model_copy(
        update={"status": "cancelled"}
    )
    return service


def _client(service: Mock | None = None):
    svc = service or _fake_service()
    app = FastAPI()
    app.state.rerun_service = svc
    app.state.api_token = ""
    app.include_router(rerun_router)
    install_error_handlers(app)
    return TestClient(app), svc


def test_create_rerun_proposal_requires_idempotency_key() -> None:
    client, _ = _client()
    response = client.post(
        "/v1/rerun-proposals",
        json={
            "parent_job_id": "job-parent",
            "expected_parent_job_version": 4,
            "expected_parent_run_manifest_sha256": "e" * 64,
            "edits": [
                {
                    "option": "--epochs",
                    "operation": "set",
                    "expected_old_value": "50",
                    "value": "100",
                }
            ],
        },
    )
    assert response.status_code == 422


def test_create_rerun_proposal_success() -> None:
    client, svc = _client()
    response = client.post(
        "/v1/rerun-proposals",
        json={
            "parent_job_id": "job-parent",
            "expected_parent_job_version": 4,
            "expected_parent_run_manifest_sha256": "e" * 64,
            "edits": [
                {
                    "option": "--epochs",
                    "operation": "set",
                    "expected_old_value": "50",
                    "value": "100",
                }
            ],
        },
        headers={"Idempotency-Key": "create-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["replayed"] is False
    assert data["proposal"]["status"] == "pending"
    svc.create_proposal.assert_called_once()


def test_create_rerun_proposal_replay() -> None:
    svc = _fake_service()
    svc.create_proposal.return_value = (_proposal_record(), False)
    client, _ = _client(svc)
    response = client.post(
        "/v1/rerun-proposals",
        json={
            "parent_job_id": "job-parent",
            "expected_parent_job_version": 4,
            "expected_parent_run_manifest_sha256": "e" * 64,
            "edits": [
                {
                    "option": "--epochs",
                    "operation": "set",
                    "expected_old_value": "50",
                    "value": "100",
                }
            ],
        },
        headers={"Idempotency-Key": "create-1"},
    )
    assert response.status_code == 200
    assert response.json()["replayed"] is True


def test_get_rerun_proposal_not_found() -> None:
    svc = _fake_service()
    svc.get_proposal.side_effect = RerunNotFoundError("not found")
    client, _ = _client(svc)
    response = client.get("/v1/rerun-proposals/nonexistent")
    assert response.status_code == 404
    assert response.json()["code"] == "RERUN_PROPOSAL_NOT_FOUND"


def test_submit_rerun_proposal_conflict() -> None:
    svc = _fake_service()
    svc.submit_proposal.side_effect = RerunConflictError("stale version")
    client, _ = _client(svc)
    record = _proposal_record()
    response = client.post(
        f"/v1/rerun-proposals/{record.proposal.proposal_id}/submit",
        json={
            "expected_proposal_hash": record.proposal.proposal_hash,
            "expected_version": record.version,
        },
        headers={"Idempotency-Key": "submit-1"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "RERUN_CONFLICT"


def test_submit_rerun_proposal_expired() -> None:
    svc = _fake_service()
    svc.submit_proposal.side_effect = RerunExpiredError("expired")
    client, _ = _client(svc)
    record = _proposal_record()
    response = client.post(
        f"/v1/rerun-proposals/{record.proposal.proposal_id}/submit",
        json={
            "expected_proposal_hash": record.proposal.proposal_hash,
            "expected_version": record.version,
        },
        headers={"Idempotency-Key": "submit-1"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "RERUN_PROPOSAL_EXPIRED"


def test_create_rerun_proposal_command_rejected() -> None:
    svc = _fake_service()
    svc.create_proposal.side_effect = RerunCommandRejectedError(
        "unsafe command"
    )
    client, _ = _client(svc)
    response = client.post(
        "/v1/rerun-proposals",
        json={
            "parent_job_id": "job-parent",
            "expected_parent_job_version": 4,
            "expected_parent_run_manifest_sha256": "e" * 64,
            "edits": [
                {
                    "option": "--epochs",
                    "operation": "set",
                    "expected_old_value": "50",
                    "value": "100",
                }
            ],
        },
        headers={"Idempotency-Key": "create-1"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "RERUN_COMMAND_REJECTED"


def test_integrity_error_does_not_leak_detail() -> None:
    svc = _fake_service()
    svc.create_proposal.side_effect = RerunIntegrityError(
        "internal: object_key=workspace/paper mismatch"
    )
    client, _ = _client(svc)
    response = client.post(
        "/v1/rerun-proposals",
        json={
            "parent_job_id": "job-parent",
            "expected_parent_job_version": 4,
            "expected_parent_run_manifest_sha256": "e" * 64,
            "edits": [
                {
                    "option": "--epochs",
                    "operation": "set",
                    "expected_old_value": "50",
                    "value": "100",
                }
            ],
        },
        headers={"Idempotency-Key": "create-1"},
    )
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "RERUN_INTEGRITY_ERROR"
    assert "object_key" not in body["message"]
    assert "workspace" not in body["message"]
