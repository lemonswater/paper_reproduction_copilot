"""Phase 46: Project Memory API 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.project_memory_routes import router as project_memory_router
from app.project_memory.evidence import ProjectJobSnapshot
from app.project_memory.repository import SqliteProjectMemoryRepository
from app.project_memory.retrieval import ProjectFactRetriever
from app.project_memory.schemas import (
    ManualFactProposalRequest,
    ProjectCreateRequest,
    ProjectFactDraftContent,
    TextFactValue,
)
from app.project_memory.service import ProjectMemoryService
from app.secrets.redaction import SecretRedactor
from tests.helpers.project_memory import NOW, fixed_clock, make_anchor


@pytest.fixture
def app_and_service(tmp_path):
    repo = SqliteProjectMemoryRepository(tmp_path / "pm.db")
    repo.initialize()

    anchor = make_anchor()
    jobs = MagicMock()
    jobs.read.return_value = ProjectJobSnapshot(anchor=anchor)

    chats = MagicMock()

    retriever = ProjectFactRetriever(
        repo,
        top_k=20,
        max_chars=20000,
        clock=fixed_clock,
    )

    redactor = SecretRedactor()

    svc = ProjectMemoryService(
        repository=repo,
        jobs=jobs,
        chats=chats,
        retriever=retriever,
        redactor=redactor,
        clock=fixed_clock,
    )

    app = FastAPI()
    app.state.project_memory_service = svc
    app.state.api_token_override = None
    app.include_router(project_memory_router)

    # Install error handlers so domain exceptions map to HTTP status codes
    from app.api.errors import install_error_handlers
    install_error_handlers(app)

    # Override auth
    from app.api.auth import require_api_auth
    app.dependency_overrides[require_api_auth] = lambda: "test-user"

    return app, svc, anchor


@pytest.fixture
def client(app_and_service):
    app, _, _ = app_and_service
    return TestClient(app)


def test_create_project_via_api(client, app_and_service):
    _, _, anchor = app_and_service
    response = client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project"]["status"] == "active"
    assert data["replayed"] is False


def test_missing_idempotency_key_returns_422(client, app_and_service):
    _, _, anchor = app_and_service
    response = client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
    )
    assert response.status_code == 422


def test_list_projects(client, app_and_service):
    _, _, anchor = app_and_service
    # Create a project first
    client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-2"},
    )
    response = client.get("/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_project(client, app_and_service):
    _, _, anchor = app_and_service
    create_resp = client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-3"},
    )
    project_id = create_resp.json()["project"]["project_id"]
    response = client.get(f"/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["project_id"] == project_id


def test_get_nonexistent_project_returns_404(client):
    response = client.get(f"/v1/projects/project_{'0' * 24}")
    assert response.status_code == 404


def test_full_fact_lifecycle_via_api(client, app_and_service):
    _, _, anchor = app_and_service
    # Create project
    create_resp = client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-4"},
    )
    project_id = create_resp.json()["project"]["project_id"]

    # Propose fact
    propose_resp = client.post(
        f"/v1/projects/{project_id}/facts/proposals",
        json={
            "content": {
                "category": "user_constraint",
                "key": "network_access",
                "value": {"kind": "text", "text": "default offline"},
            },
            "source_note": "API test proposal",
        },
        headers={"Idempotency-Key": "api-propose-1"},
    )
    assert propose_resp.status_code == 200
    fact_id = propose_resp.json()["fact"]["fact_id"]
    fact_version = propose_resp.json()["fact"]["version"]
    fact_hash = propose_resp.json()["fact"]["record_hash"]

    # Confirm fact
    confirm_resp = client.post(
        f"/v1/projects/{project_id}/facts/{fact_id}/confirm",
        json={
            "expected_version": fact_version,
            "expected_record_hash": fact_hash,
            "reason": "API test confirm",
        },
        headers={"Idempotency-Key": "api-confirm-1"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["fact"]["status"] == "confirmed"

    # Get fact context
    context_resp = client.get(f"/v1/projects/{project_id}/facts/context")
    assert context_resp.status_code == 200
    pack = context_resp.json()
    assert len(pack["items"]) == 1
    assert pack["items"][0]["fact_id"] == fact_id

    # List facts
    list_resp = client.get(f"/v1/projects/{project_id}/facts")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # Revoke fact
    revoked_version = confirm_resp.json()["fact"]["version"]
    revoked_hash = confirm_resp.json()["fact"]["record_hash"]
    revoke_resp = client.post(
        f"/v1/projects/{project_id}/facts/{fact_id}/revoke",
        json={
            "expected_version": revoked_version,
            "expected_record_hash": revoked_hash,
            "reason": "API test revoke",
        },
        headers={"Idempotency-Key": "api-revoke-1"},
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["fact"]["status"] == "revoked"

    # Delete fact (terminal can be deleted)
    deleted_version = revoke_resp.json()["fact"]["version"]
    deleted_hash = revoke_resp.json()["fact"]["record_hash"]
    delete_resp = client.post(
        f"/v1/projects/{project_id}/facts/{fact_id}/delete",
        json={
            "expected_version": deleted_version,
            "expected_record_hash": deleted_hash,
            "reason": "API test delete",
        },
        headers={"Idempotency-Key": "api-delete-1"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["fact"]["status"] == "deleted"
    assert delete_resp.json()["fact"]["content"] is None

    # List with include_terminal
    list_terminal_resp = client.get(
        f"/v1/projects/{project_id}/facts",
        params={"include_terminal": True},
    )
    assert list_terminal_resp.status_code == 200
    assert any(f["status"] == "deleted" for f in list_terminal_resp.json())


def test_stale_version_returns_409(client, app_and_service):
    _, _, anchor = app_and_service
    create_resp = client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-5"},
    )
    project_id = create_resp.json()["project"]["project_id"]
    propose_resp = client.post(
        f"/v1/projects/{project_id}/facts/proposals",
        json={
            "content": {
                "category": "user_constraint",
                "key": "network_access",
                "value": {"kind": "text", "text": "default offline"},
            },
            "source_note": "API test proposal",
        },
        headers={"Idempotency-Key": "api-propose-2"},
    )
    fact_id = propose_resp.json()["fact"]["fact_id"]
    confirm_resp = client.post(
        f"/v1/projects/{project_id}/facts/{fact_id}/confirm",
        json={
            "expected_version": 99,
            "expected_record_hash": "0" * 64,
            "reason": "stale",
        },
        headers={"Idempotency-Key": "api-confirm-stale"},
    )
    assert confirm_resp.status_code == 409


def test_same_key_different_body_returns_409(client, app_and_service):
    _, _, anchor = app_and_service
    client.post(
        "/v1/projects",
        json={
            "display_name": "API Test Project",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-6"},
    )
    # Same key, different body
    response = client.post(
        "/v1/projects",
        json={
            "display_name": "Different Name",
            "anchor_job_id": anchor.job_id,
            "expected_anchor_job_version": anchor.job_version,
            "expected_workspace_manifest_hash": anchor.workspace_manifest_hash,
        },
        headers={"Idempotency-Key": "api-create-6"},
    )
    assert response.status_code == 409
