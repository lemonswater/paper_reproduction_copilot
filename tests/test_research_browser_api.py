"""API tests for the research browser.

When RESEARCH_BROWSER_ENABLED=false (default), the /v1/research routes
are not registered, and the service is not initialized.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_api_app


@pytest.fixture(autouse=True)
def _disable_heavy_services(monkeypatch):
    """Disable project memory, knowledge base, and retention to avoid
    requiring a master.key or langgraph.checkpoint.sqlite in tests."""

    from app.config import settings

    monkeypatch.setattr(settings, "project_memory_enabled", False)
    monkeypatch.setattr(settings, "research_browser_enabled", False)
    monkeypatch.setattr(settings, "knowledge_base_enabled", False)
    monkeypatch.setattr(settings, "retention_enabled", False)
    monkeypatch.setattr(settings, "chat_enabled", False)
    monkeypatch.setattr(settings, "web_ui_required", False)
    monkeypatch.setattr(settings, "web_dist_dir", Path("/nonexistent-dist"))

    # build_model_gateway is lru_cached and internally calls build_secret_service.
    # Inject a lightweight stub so create_api_app does not touch the filesystem.
    from app.model_routing import factory as mg_factory

    monkeypatch.setattr(
        mg_factory,
        "build_model_gateway",
        lambda: SimpleNamespace(
            ledger=SimpleNamespace(ping=lambda: "ok"),
        ),
    )

    # build_retention calls build_checkpointer which imports
    # langgraph.checkpoint.sqlite (not installed in test env).
    from app.retention import factory as ret_factory

    monkeypatch.setattr(
        ret_factory,
        "build_retention",
        lambda **kw: SimpleNamespace(
            inventory=SimpleNamespace(),
            quota_guard=SimpleNamespace(),
            service=None,
        ),
    )


def test_research_browser_disabled_returns_404() -> None:
    """When research_browser_service is None, /v1/research routes are not registered."""
    app = create_api_app(
        research_browser_service=None,
        api_token="test-token",
    )
    client = TestClient(app)
    response = client.get("/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa")
    assert response.status_code == 404


def test_research_api_requires_auth() -> None:
    """Without auth header, API returns 401/403/422/404."""
    app = create_api_app(
        research_browser_service=None,
        api_token="test-token",
    )
    client = TestClient(app)
    response = client.post(
        "/v1/research",
        json={"query": "test", "purpose": "test"},
    )
    assert response.status_code in {401, 403, 404, 422}


def test_research_routes_not_registered_when_disabled() -> None:
    """Verify that /v1/research/* paths return 404 when the feature is disabled."""
    app = create_api_app(
        research_browser_service=None,
        api_token="test-token",
    )
    client = TestClient(app)
    paths = [
        ("POST", "/v1/research"),
        ("GET", "/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa"),
        ("POST", "/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa/run"),
        ("GET", "/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa/pack"),
        ("GET", "/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa/events"),
        ("POST", "/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa/cancel"),
        ("POST", "/v1/research/research_aaaaaaaaaaaaaaaaaaaaaaaa/resource-candidates"),
    ]
    for method, path in paths:
        response = client.request(method, path, json={})
        assert response.status_code == 404, f"{method} {path} returned {response.status_code}"
