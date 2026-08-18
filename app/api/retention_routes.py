"""Phase 35 Retention API 路由。"""
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from app.api.auth import require_api_auth
from app.retention.errors import RetentionBackendUnsupported
from app.retention.schemas import (
    CleanupPlanView,
    CleanupResultView,
    HoldRequest,
    PlanConfirmRequest,
    RetentionHold,
    StorageSummaryView,
)

router = APIRouter(prefix="/v1")
Actor = Annotated[str, Depends(require_api_auth)]

def _bundle(request: Request):
    return request.app.state.retention_bundle

def _service(request: Request):
    service = _bundle(request).service
    if service is None:
        raise RetentionBackendUnsupported(
            "当前 backend 只支持容量盘点，不支持 destructive GC"
        )
    return service

@router.get("/storage/summary", response_model=StorageSummaryView)
def storage_summary(request: Request, _actor: Actor) -> StorageSummaryView:
    return StorageSummaryView.from_summary(
        _bundle(request).inventory.summarize()
    )

@router.post("/retention/plans", response_model=CleanupPlanView, status_code=201)
def create_plan(request: Request, _actor: Actor) -> CleanupPlanView:
    return CleanupPlanView.from_plan(_service(request).create_plan())

@router.get("/retention/plans/{plan_id}", response_model=CleanupPlanView)
def get_plan(plan_id: str, request: Request, _actor: Actor) -> CleanupPlanView:
    return CleanupPlanView.from_plan(_service(request).get_plan(plan_id))

@router.post(
    "/retention/plans/{plan_id}/confirm",
    response_model=CleanupPlanView,
)
def confirm_plan(
    plan_id: str,
    body: PlanConfirmRequest,
    request: Request,
    _actor: Actor,
) -> CleanupPlanView:
    return CleanupPlanView.from_plan(
        _service(request).confirm_plan(
            plan_id=plan_id,
            plan_hash=body.plan_hash,
        )
    )

@router.post(
    "/retention/plans/{plan_id}/sweep",
    response_model=CleanupResultView,
)
def sweep_plan(
    plan_id: str,
    body: PlanConfirmRequest,
    request: Request,
    _actor: Actor,
) -> CleanupResultView:
    return CleanupResultView.from_result(
        _service(request).sweep(
            plan_id=plan_id,
            plan_hash=body.plan_hash,
        )
    )

@router.get("/retention/holds", response_model=list[RetentionHold])
def list_holds(request: Request, _actor: Actor) -> list[RetentionHold]:
    return _service(request).list_holds()

@router.put("/retention/holds/{job_id}", response_model=RetentionHold)
def put_hold(
    job_id: str,
    body: HoldRequest,
    request: Request,
    actor: Actor,
) -> RetentionHold:
    return _service(request).create_hold(
        job_id=job_id,
        reason=body.reason,
        actor=actor,
    )

@router.delete("/retention/holds/{job_id}", status_code=204)
def delete_hold(job_id: str, request: Request, _actor: Actor) -> None:
    _service(request).delete_hold(job_id)