"""Phase 30 UI API 测试。"""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.ui_routes as ui_routes
from app.api.ui_routes import router
from app.config import settings
from app.interaction.service import _public_input_name
from tests.helpers.interaction import make_job


class FakeInteractionService:
    def get_job(self, job_id: str):
        assert job_id == "job-1"
        return make_job()

    def events_after(self, **kwargs):
        assert kwargs["after_event_id"] == 0
        return []


def _client() -> TestClient:
    app = FastAPI()
    app.state.api_token = None
    app.state.interaction_service = (
        FakeInteractionService()
    )
    app.include_router(router)
    return TestClient(app)


def test_ui_config_only_contains_public_profile_fields(
    monkeypatch,
):
    profile = SimpleNamespace(
        profile_id="safe-local",
        backend="native",
        enforcement_mode="strict",
        network_policy="none",
        workspace_root="/must/not/leak",
        env={"SECRET": "must-not-leak"},
    )
    monkeypatch.setattr(
        ui_routes,
        "load_execution_profiles",
        lambda: {"safe-local": profile},
    )
    monkeypatch.setattr(
        settings,
        "default_execution_profile",
        "safe-local",
    )

    response = _client().get("/v1/ui/config")

    assert response.status_code == 200
    encoded = response.text
    assert "safe-local" in encoded
    assert "workspace_root" not in encoded
    assert "must-not-leak" not in encoded


def test_timeline_endpoint_returns_public_projection():
    response = _client().get("/v1/ui/jobs/job-1/timeline")

    assert response.status_code == 200
    assert response.json()["job"]["job_id"] == "job-1"
    assert response.json()["items"][0]["role"] == "user"


def test_resource_input_name_does_not_call_path_on_none():
    resource = SimpleNamespace(
        kind="paper_pdf",
        resource_id="resource-1",
    )

    assert _public_input_name(
        local_path=None,
        resource=resource,
        fallback="paper",
    ) == "paper_pdf:resource-1"
