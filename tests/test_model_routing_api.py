"""Phase 50: Model Routing API 只读端点测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import require_api_auth
from app.api.model_routing_routes import router as model_routing_router
from app.model_routing.errors import (
    ModelBudgetExceeded,
    ModelLedgerIntegrityError,
)
from app.model_routing.gateway import ModelGateway
from app.model_routing.schemas import (
    ModelBudgetSummary,
    ModelInvocationRecord,
)
from tests.helpers.model_routing import (
    FakeProviders,
    TEST_PRICING,
    ModelBudgetPolicy,
    build_test_document,
    build_test_gateway,
)


class FakeGateway:
    """用于 API 测试的 Gateway mock。"""

    def __init__(self, *, budget_summary=None, invocations=None):
        self._budget_summary = budget_summary or ModelBudgetSummary(
            utc_date="2026-01-01",
            job_id=None,
            settled_input_tokens=0,
            settled_output_tokens=0,
            active_reserved_tokens=0,
            settled_cost_micro_usd=0,
            active_reserved_cost_micro_usd=0,
            invocation_count=0,
            active_reservation_count=0,
            unpriced_invocation_count=0,
        )
        self._invocations = invocations or []

        class _FakeLedger:
            def summary(inner_self, *, utc_date, job_id=None):
                return self._budget_summary

            def list_invocations(inner_self, *, job_id=None, limit=100):
                return self._invocations[:limit]

            def ping(inner_self):
                return None

        self.ledger = _FakeLedger()
        self.mode = "off"
        self.router = None
        self.providers = None


def _create_test_app(gateway: Any) -> FastAPI:
    app = FastAPI()
    app.state.model_gateway = gateway
    app.include_router(model_routing_router)
    return app


def _create_authed_app(gateway: Any) -> FastAPI:
    """创建带 auth 的测试 app，使用 dependency override 绕过认证。"""
    from app.api.errors import install_error_handlers

    app = FastAPI()
    app.state.model_gateway = gateway
    app.dependency_overrides[require_api_auth] = lambda: "test-user"
    app.include_router(model_routing_router)
    install_error_handlers(app)
    return app


def test_get_budget_summary(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get("/v1/model-routing/budget")
    assert response.status_code == 200
    data = response.json()
    assert "utc_date" in data
    assert "invocation_count" in data


def test_get_budget_summary_with_date(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get(
        "/v1/model-routing/budget?utc_date=2026-08-12"
    )
    assert response.status_code == 200


def test_get_budget_summary_with_job_id(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get(
        "/v1/model-routing/budget?job_id=job-123"
    )
    assert response.status_code == 200


def test_list_invocations(tmp_path: Path):
    gateway = FakeGateway(invocations=[])
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get("/v1/model-routing/invocations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_invocations_with_limit(tmp_path: Path):
    gateway = FakeGateway(invocations=[])
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get(
        "/v1/model-routing/invocations?limit=10"
    )
    assert response.status_code == 200


def test_list_invocations_limit_too_large(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get(
        "/v1/model-routing/invocations?limit=501"
    )
    assert response.status_code == 422


def test_list_invocations_limit_too_small(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.get(
        "/v1/model-routing/invocations?limit=0"
    )
    assert response.status_code == 422


def test_no_put_policy_endpoint(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.put("/v1/model-routing/policy")
    assert response.status_code == 405 or response.status_code == 404


def test_no_post_budget_endpoint(tmp_path: Path):
    gateway = FakeGateway()
    app = _create_authed_app(gateway)
    client = TestClient(app)

    response = client.post("/v1/model-routing/budget")
    assert response.status_code == 405 or response.status_code == 404


def test_model_budget_exceeded_maps_to_429(tmp_path: Path):
    from app.api.errors import install_error_handlers

    app = FastAPI()

    class _RaisingLedger:
        def ping(inner_self):
            return None

        def summary(inner_self, *, utc_date, job_id=None):
            raise ModelBudgetExceeded(
                scope="daily",
                limit=10000,
                used_or_reserved=10000,
                requested=5000,
            )

        def list_invocations(inner_self, *, job_id=None, limit=100):
            return []

    class _RaisingGateway:
        mode = "active"
        ledger = _RaisingLedger()
        router = None
        providers = None

    app.state.model_gateway = _RaisingGateway()
    app.dependency_overrides[require_api_auth] = lambda: "test-user"
    app.include_router(model_routing_router)
    install_error_handlers(app)
    client = TestClient(app)

    response = client.get("/v1/model-routing/budget")
    assert response.status_code == 429
    data = response.json()
    assert data["code"] == "MODEL_BUDGET_EXCEEDED"
    # Should not leak scope/job/path
    assert "daily" not in response.text


def test_ledger_integrity_error_maps_to_503(tmp_path: Path):
    from app.api.errors import install_error_handlers

    app = FastAPI()

    class _RaisingLedger:
        def ping(inner_self):
            return None

        def summary(inner_self, *, utc_date, job_id=None):
            raise ModelLedgerIntegrityError("corrupted row")

        def list_invocations(inner_self, *, job_id=None, limit=100):
            return []

    class _RaisingGateway:
        mode = "active"
        ledger = _RaisingLedger()
        router = None
        providers = None

    app.state.model_gateway = _RaisingGateway()
    app.dependency_overrides[require_api_auth] = lambda: "test-user"
    app.include_router(model_routing_router)
    install_error_handlers(app)
    client = TestClient(app)

    response = client.get("/v1/model-routing/budget")
    assert response.status_code == 503
    data = response.json()
    assert data["code"] == "MODEL_LEDGER_UNAVAILABLE"
