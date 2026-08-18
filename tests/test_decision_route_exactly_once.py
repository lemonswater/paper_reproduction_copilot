from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import install_error_handlers
from app.api.routes import router
from app.job_runtime.errors import JobConflictError
from app.observability.noop import NoOpTelemetry


class CountingConflictService:
    def __init__(self):
        self.calls = 0

    def submit_decision(self, **_kwargs):
        self.calls += 1
        raise JobConflictError("stale decision")


def test_business_conflict_does_not_repeat_mutation():
    service = CountingConflictService()
    app = FastAPI()
    app.state.api_token = None
    app.state.telemetry = NoOpTelemetry()
    app.state.interaction_service = service
    app.include_router(router)
    install_error_handlers(app)
    client = TestClient(app)

    response = client.post(
        "/v1/jobs/job-1/decisions",
        headers={
            "Idempotency-Key": "exactly-once-route-test"
        },
        json={
            "expected_job_version": 4,
            "expected_wait_generation": 2,
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
                "feedback": None,
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"
    assert service.calls == 1
