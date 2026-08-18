"""Phase 29 Resource API 测试。

API endpoints:
- POST /v1/resources
- GET  /v1/resources/{resource_id}
- GET  /v1/resources/{resource_id}/events
- POST /v1/resources/{resource_id}/decision
- POST /v1/resources/{resource_id}/cancel

第一版所有 submit 结果都是 awaiting_approval。
Decision body 必须包含 request_sha256。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.resource_routes import router
from app.resources.service import ResourceService
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)

AUTH = {"Authorization": "Bearer test-token"}


def _app() -> tuple[FastAPI, ResourceService]:
    repository = FakeResourceRepository()
    service = ResourceService(repository)
    app = FastAPI()
    app.include_router(router)
    app.state.resource_service = service
    app.state.api_token = "test-token"
    return app, service


def _client() -> tuple[TestClient, ResourceService]:
    app, service = _app()
    return TestClient(app), service


def _submit_pdf(
    client: TestClient,
    *,
    idempotency_key: str = "key1",
    url: str = "https://arxiv.org/pdf/1234.5678",
) -> dict:
    response = client.post(
        "/v1/resources",
        headers={
            **AUTH,
            "Idempotency-Key": idempotency_key,
        },
        json={
            "kind": "paper_pdf",
            "source_url": url,
            "purpose": "test paper",
        },
    )
    assert response.status_code == 201
    return response.json()


class TestSubmitResource:
    def test_submit_returns_awaiting_approval(
        self,
    ) -> None:
        client, _ = _client()
        result = _submit_pdf(client)
        assert (
            result["resource"]["status"]
            == "awaiting_approval"
        )
        assert (
            result["resource"]["kind"] == "paper_pdf"
        )
        assert result["replayed"] is False

    def test_submit_idempotent(
        self,
    ) -> None:
        client, _ = _client()
        r1 = _submit_pdf(client, idempotency_key="same")
        r2 = _submit_pdf(client, idempotency_key="same")
        assert (
            r1["resource"]["resource_id"]
            == r2["resource"]["resource_id"]
        )
        assert r2["replayed"] is True

    def test_submit_requires_auth(self) -> None:
        client, _ = _client()
        response = client.post(
            "/v1/resources",
            headers={"Idempotency-Key": "key"},
            json={
                "kind": "paper_pdf",
                "source_url": "https://arxiv.org/pdf/1234",
                "purpose": "test",
            },
        )
        assert response.status_code in (
            401,
            403,
        )

    def test_submit_requires_idempotency_key(
        self,
    ) -> None:
        client, _ = _client()
        response = client.post(
            "/v1/resources",
            headers=AUTH,
            json={
                "kind": "paper_pdf",
                "source_url": "https://arxiv.org/pdf/1234",
                "purpose": "test",
            },
        )
        assert response.status_code == 422

    def test_submit_checkpoint_without_sha_rejected(
        self,
    ) -> None:
        client, _ = _client()
        response = client.post(
            "/v1/resources",
            headers={
                **AUTH,
                "Idempotency-Key": "ckpt1",
            },
            json={
                "kind": "checkpoint",
                "source_url": "https://arxiv.org/model.pt",
                "purpose": "weights",
            },
        )
        assert response.status_code == 422


class TestGetResource:
    def test_get_existing(self) -> None:
        client, _ = _client()
        result = _submit_pdf(client)
        rid = result["resource"]["resource_id"]
        response = client.get(
            f"/v1/resources/{rid}",
            headers=AUTH,
        )
        assert response.status_code == 200
        assert (
            response.json()["resource_id"] == rid
        )

    def test_get_nonexistent_404(self) -> None:
        client, _ = _client()
        response = client.get(
            "/v1/resources/res_missing",
            headers=AUTH,
        )
        assert response.status_code == 404


class TestDecision:
    def test_approve_resource(self) -> None:
        client, _ = _client()
        result = _submit_pdf(client)
        rid = result["resource"]["resource_id"]
        request_sha = result["resource"][
            "request_sha256"
        ]

        response = client.post(
            f"/v1/resources/{rid}/decision",
            headers=AUTH,
            json={
                "decision": "approved",
                "request_sha256": request_sha,
                "reason": "approved by operator",
            },
        )
        assert response.status_code == 200
        assert (
            response.json()["resource"]["status"]
            == "queued"
        )

    def test_reject_resource(self) -> None:
        client, _ = _client()
        result = _submit_pdf(client)
        rid = result["resource"]["resource_id"]
        request_sha = result["resource"][
            "request_sha256"
        ]

        response = client.post(
            f"/v1/resources/{rid}/decision",
            headers=AUTH,
            json={
                "decision": "rejected",
                "request_sha256": request_sha,
            },
        )
        assert response.status_code == 200
        assert (
            response.json()["resource"]["status"]
            == "rejected"
        )

    def test_decision_nonexistent_404(
        self,
    ) -> None:
        client, _ = _client()
        response = client.post(
            "/v1/resources/res_missing/decision",
            headers=AUTH,
            json={
                "decision": "approved",
                "request_sha256": "a" * 64,
            },
        )
        assert response.status_code == 404


class TestCancel:
    def test_cancel_resource(self) -> None:
        client, _ = _client()
        result = _submit_pdf(client)
        rid = result["resource"]["resource_id"]

        response = client.post(
            f"/v1/resources/{rid}/cancel",
            headers=AUTH,
            json={"reason": "user cancelled"},
        )
        assert response.status_code == 200
        assert (
            response.json()["resource"]["status"]
            == "cancelled"
        )

    def test_cancel_nonexistent_404(
        self,
    ) -> None:
        client, _ = _client()
        response = client.post(
            "/v1/resources/res_missing/cancel",
            headers=AUTH,
            json={"reason": "cancel"},
        )
        assert response.status_code == 404


class TestEvents:
    def test_list_events(self) -> None:
        client, _ = _client()
        result = _submit_pdf(client)
        rid = result["resource"]["resource_id"]

        response = client.get(
            f"/v1/resources/{rid}/events",
            headers=AUTH,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert any(
            e["event_type"] == "resource_submitted"
            for e in data["items"]
        )

    def test_events_nonexistent_404(
        self,
    ) -> None:
        client, _ = _client()
        response = client.get(
            "/v1/resources/res_missing/events",
            headers=AUTH,
        )
        assert response.status_code == 404


class TestSourceUrlSanitization:
    def test_response_does_not_expose_claim_token(
        self,
    ) -> None:
        client, service = _client()
        result = _submit_pdf(client)
        rid = result["resource"]["resource_id"]

        # 批准后 claim，确认 response 不含 claim_token。
        request_sha = result["resource"][
            "request_sha256"
        ]
        client.post(
            f"/v1/resources/{rid}/decision",
            headers=AUTH,
            json={
                "decision": "approved",
                "request_sha256": request_sha,
            },
        )
        record = service.repository.claim_next(
            worker_id="w1",
            lease_seconds=60,
        )
        assert record is not None

        response = client.get(
            f"/v1/resources/{rid}",
            headers=AUTH,
        )
        body = response.json()
        assert "claim_token" not in body
        assert body["status"] == "fetching"
