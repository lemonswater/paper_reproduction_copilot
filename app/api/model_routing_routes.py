from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.auth import require_api_auth
from app.model_routing.gateway import ModelGateway
from app.model_routing.schemas import (
    ModelBudgetSummary,
    ModelInvocationRecord,
)


router = APIRouter(
    prefix="/v1/model-routing",
    tags=["model-routing"],
)
Actor = Annotated[str, Depends(require_api_auth)]


def gateway(request: Request) -> ModelGateway:
    return request.app.state.model_gateway


Gateway = Annotated[ModelGateway, Depends(gateway)]


@router.get("/budget", response_model=ModelBudgetSummary)
def get_budget_summary(
    actor: Actor,
    model_gateway: Gateway,
    utc_date: str | None = None,
    job_id: str | None = None,
):
    del actor
    selected_date = (
        utc_date
        or datetime.now(timezone.utc).date().isoformat()
    )
    return model_gateway.ledger.summary(
        utc_date=selected_date,
        job_id=job_id,
    )


@router.get(
    "/invocations",
    response_model=list[ModelInvocationRecord],
)
def list_model_invocations(
    actor: Actor,
    model_gateway: Gateway,
    job_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    del actor
    return model_gateway.ledger.list_invocations(
        job_id=job_id,
        limit=limit,
    )
