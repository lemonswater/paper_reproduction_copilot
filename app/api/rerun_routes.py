# app/api/rerun_routes.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.api.auth import require_api_auth
from app.rerun.schemas import (
    RerunProposalCancelRequest,
    RerunProposalCreateRequest,
    RerunProposalMutationResponse,
    RerunProposalRecord,
    RerunProposalSubmitRequest,
    RerunSubmissionResponse,
)
from app.rerun.service import RerunService

router = APIRouter(prefix="/v1")

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=300,
    ),
]
Actor = Annotated[str, Depends(require_api_auth)]


def rerun_service(request: Request) -> RerunService:
    return request.app.state.rerun_service


RerunDependency = Annotated[
    RerunService,
    Depends(rerun_service),
]


@router.post(
    "/rerun-proposals",
    response_model=RerunProposalMutationResponse,
)
def create_rerun_proposal(
    body: RerunProposalCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: RerunDependency,
) -> RerunProposalMutationResponse:
    del actor
    record, created = service.create_proposal(
        request=body,
        idempotency_key=idempotency_key,
    )
    return RerunProposalMutationResponse(
        proposal=record,
        replayed=not created,
    )


@router.get(
    "/rerun-proposals/{proposal_id}",
    response_model=RerunProposalRecord,
)
def get_rerun_proposal(
    proposal_id: str,
    actor: Actor,
    service: RerunDependency,
) -> RerunProposalRecord:
    del actor
    return service.get_proposal(proposal_id)


@router.post(
    "/rerun-proposals/{proposal_id}/submit",
    response_model=RerunSubmissionResponse,
)
def submit_rerun_proposal(
    proposal_id: str,
    body: RerunProposalSubmitRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: RerunDependency,
) -> RerunSubmissionResponse:
    del actor
    record, job, created = service.submit_proposal(
        proposal_id=proposal_id,
        request=body,
        idempotency_key=idempotency_key,
    )
    return RerunSubmissionResponse(
        proposal=record,
        child_job_id=job.job_id,
        job_created=created,
    )


@router.post(
    "/rerun-proposals/{proposal_id}/cancel",
    response_model=RerunProposalRecord,
)
def cancel_rerun_proposal(
    proposal_id: str,
    body: RerunProposalCancelRequest,
    actor: Actor,
    service: RerunDependency,
) -> RerunProposalRecord:
    del actor
    return service.cancel_proposal(
        proposal_id=proposal_id,
        request=body,
    )
