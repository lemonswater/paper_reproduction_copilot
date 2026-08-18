from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.auth import require_api_auth
from app.failure_memory.schemas import (
    FailureCaseConfirmRequest,
    FailureCaseCreateRequest,
    FailureCaseDeprecateRequest,
    FailureCaseMutationResponse,
    FailureCasePack,
    FailureCaseRecord,
    FailureCaseVerifyRequest,
)
from app.failure_memory.service import FailureCaseService


router = APIRouter(prefix="/v1/failure-cases")

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=300,
    ),
]
Actor = Annotated[str, Depends(require_api_auth)]


def failure_case_service(request: Request) -> FailureCaseService:
    return request.app.state.failure_case_service


FailureCaseDependency = Annotated[
    FailureCaseService,
    Depends(failure_case_service),
]


@router.post(
    "/candidates",
    response_model=FailureCaseMutationResponse,
)
def create_candidate(
    body: FailureCaseCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: FailureCaseDependency,
) -> FailureCaseMutationResponse:
    del actor
    return service.create_candidate(
        request=body,
        idempotency_key=idempotency_key,
    )


@router.get("", response_model=list[FailureCaseRecord])
def list_cases(
    actor: Actor,
    service: FailureCaseDependency,
    include_deprecated: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[FailureCaseRecord]:
    del actor
    return service.list_cases(
        include_deprecated=include_deprecated,
        limit=limit,
    )


# 固定路径必须定义在 /{case_id} 前，避免 source-job 被当成 case_id。
@router.get(
    "/source-job/{job_id}/matches",
    response_model=FailureCasePack,
)
def search_source_job(
    job_id: str,
    actor: Actor,
    service: FailureCaseDependency,
) -> FailureCasePack:
    del actor
    return service.search_source_job(job_id)


@router.get("/{case_id}", response_model=FailureCaseRecord)
def get_case(
    case_id: str,
    actor: Actor,
    service: FailureCaseDependency,
) -> FailureCaseRecord:
    del actor
    return service.get(case_id)


@router.post(
    "/{case_id}/confirm",
    response_model=FailureCaseMutationResponse,
)
def confirm_case(
    case_id: str,
    body: FailureCaseConfirmRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: FailureCaseDependency,
) -> FailureCaseMutationResponse:
    return service.confirm(
        case_id=case_id,
        request=body,
        idempotency_key=idempotency_key,
        actor=actor,
    )


@router.post(
    "/{case_id}/verify",
    response_model=FailureCaseMutationResponse,
)
def verify_case(
    case_id: str,
    body: FailureCaseVerifyRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: FailureCaseDependency,
) -> FailureCaseMutationResponse:
    del actor
    return service.verify(
        case_id=case_id,
        request=body,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{case_id}/deprecate",
    response_model=FailureCaseMutationResponse,
)
def deprecate_case(
    case_id: str,
    body: FailureCaseDeprecateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: FailureCaseDependency,
) -> FailureCaseMutationResponse:
    del actor
    return service.deprecate(
        case_id=case_id,
        request=body,
        idempotency_key=idempotency_key,
    )
