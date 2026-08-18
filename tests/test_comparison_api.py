from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.comparison_routes import router
from app.api.errors import install_error_handlers
from app.comparison.errors import ComparisonNotFoundError
from app.comparison.schemas import (
    ComparisonListItem,
    ComparisonListResponse,
)
from tests.helpers.comparison import make_report


class FakeComparisonService:
    def __init__(self):
        self.report = make_report()
        self.last_request = None

    def create(self, request):
        self.last_request = request
        return self.report

    def get(self, comparison_id: str):
        if comparison_id != self.report.comparison_id:
            raise ComparisonNotFoundError("comparison missing")
        return self.report

    def list_for_job(self, job_id: str, *, limit: int = 100):
        del limit
        if job_id not in {"job-base", "job-target"}:
            return ComparisonListResponse(items=[], count=0)
        item = ComparisonListItem.from_report(self.report)
        return ComparisonListResponse(items=[item], count=1)


def _client() -> tuple[TestClient, FakeComparisonService]:
    service = FakeComparisonService()
    app = FastAPI()
    app.state.api_token = ""
    app.state.comparison_service = service
    app.include_router(router)
    install_error_handlers(app)
    return TestClient(app), service


def test_create_get_and_list_comparison_api() -> None:
    client, service = _client()
    created = client.post(
        "/v1/comparisons",
        json={
            "base_job_id": "job-base",
            "target_job_id": "job-target",
            "allow_cross_paper": False,
        },
    )
    assert created.status_code == 201
    comparison_id = created.json()["comparison_id"]
    assert service.last_request.base_job_id == "job-base"

    fetched = client.get(f"/v1/comparisons/{comparison_id}")
    assert fetched.status_code == 200
    assert fetched.json()["comparison_hash"] == service.report.comparison_hash

    listed = client.get("/v1/jobs/job-target/comparisons")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


def test_missing_comparison_uses_stable_api_error() -> None:
    client, _service = _client()
    response = client.get(
        "/v1/comparisons/comparison_ffffffffffffffffffffffff"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "COMPARISON_NOT_FOUND"
