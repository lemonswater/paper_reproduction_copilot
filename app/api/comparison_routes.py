from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth import require_api_auth
from app.comparison.schemas import (
    ComparisonCreateRequest,
    ComparisonListResponse,
    ComparisonReport,
)
from app.comparison.service import ComparisonService


router = APIRouter(prefix="/v1")
Actor = Annotated[str, Depends(require_api_auth)]


def comparison_service(request: Request) -> ComparisonService:
    return request.app.state.comparison_service


ComparisonDependency = Annotated[
    ComparisonService,
    Depends(comparison_service),
]


@router.post(
    "/comparisons",
    response_model=ComparisonReport,
    status_code=status.HTTP_201_CREATED,
)
def create_comparison(
    body: ComparisonCreateRequest,
    _actor: Actor,
    service: ComparisonDependency,
) -> ComparisonReport:
    return service.create(body)


@router.get(
    "/comparisons/{comparison_id}",
    response_model=ComparisonReport,
)
def get_comparison(
    comparison_id: str,
    _actor: Actor,
    service: ComparisonDependency,
) -> ComparisonReport:
    return service.get(comparison_id)


@router.get(
    "/jobs/{job_id}/comparisons",
    response_model=ComparisonListResponse,
)
def list_job_comparisons(
    job_id: str,
    _actor: Actor,
    service: ComparisonDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ComparisonListResponse:
    return service.list_for_job(job_id, limit=limit)
