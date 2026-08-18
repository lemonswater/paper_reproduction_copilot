from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.auth import require_api_auth
from app.project_memory.schemas import (
    ChatFactProposalRequest,
    FactConfirmRequest,
    FactCorrectRequest,
    FactTerminalRequest,
    ManualFactProposalRequest,
    ProjectArchiveRequest,
    ProjectBindJobRequest,
    ProjectCreateRequest,
    ProjectFactCorrectionResponse,
    ProjectFactMutationResponse,
    ProjectFactPack,
    ProjectFactRecord,
    ProjectJobBinding,
    ProjectMutationResponse,
    ProjectRecord,
)
from app.project_memory.service import ProjectMemoryService


router = APIRouter(prefix="/v1/projects", tags=["project-memory"])
Actor = Annotated[str, Depends(require_api_auth)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=300),
]


def service(request: Request):
    return request.app.state.project_memory_service


Service = Annotated[ProjectMemoryService, Depends(service)]


@router.post("", response_model=ProjectMutationResponse)
def create_project(
    body: ProjectCreateRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    return svc.create_project(
        request=body, idempotency_key=key, actor=actor
    )


@router.get("", response_model=list[ProjectRecord])
def list_projects(
    actor: Actor,
    svc: Service,
    include_archived: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
):
    del actor
    return svc.repository.list_projects(
        include_archived=include_archived,
        limit=limit,
    )


@router.get("/{project_id}", response_model=ProjectRecord)
def get_project(project_id: str, actor: Actor, svc: Service):
    del actor
    return svc.repository.get_project(project_id)


@router.post("/{project_id}/archive", response_model=ProjectMutationResponse)
def archive_project(
    project_id: str,
    body: ProjectArchiveRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    return svc.archive_project(
        project_id=project_id,
        request=body,
        idempotency_key=key,
        actor=actor,
    )


@router.post("/{project_id}/jobs", response_model=ProjectJobBinding)
def bind_job(
    project_id: str,
    body: ProjectBindJobRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
    expected_project_version: int = Header(alias="X-Project-Version"),
    expected_project_hash: str = Header(alias="X-Project-Hash"),
):
    return svc.bind_job(
        project_id=project_id,
        request=body,
        expected_project_version=expected_project_version,
        expected_project_hash=expected_project_hash,
        idempotency_key=key,
        actor=actor,
    )


@router.post(
    "/{project_id}/facts/proposals",
    response_model=ProjectFactMutationResponse,
)
def propose_manual(
    project_id: str,
    body: ManualFactProposalRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    return svc.propose_manual(
        project_id=project_id,
        request=body,
        idempotency_key=key,
        actor=actor,
    )


@router.post(
    "/{project_id}/facts/from-chat",
    response_model=ProjectFactMutationResponse,
)
def propose_from_chat(
    project_id: str,
    body: ChatFactProposalRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    return svc.propose_from_chat(
        project_id=project_id,
        request=body,
        idempotency_key=key,
        actor=actor,
    )


@router.get("/{project_id}/facts", response_model=list[ProjectFactRecord])
def list_facts(
    project_id: str,
    actor: Actor,
    svc: Service,
    include_terminal: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
):
    del actor
    return svc.repository.list_facts(
        project_id=project_id,
        include_terminal=include_terminal,
        limit=limit,
    )


@router.get("/{project_id}/facts/context", response_model=ProjectFactPack)
def fact_context(project_id: str, actor: Actor, svc: Service):
    del actor
    return svc.retriever.for_project(project_id)


@router.post(
    "/{project_id}/facts/{fact_id}/confirm",
    response_model=ProjectFactMutationResponse,
)
def confirm_fact(
    project_id: str,
    fact_id: str,
    body: FactConfirmRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    fact = svc.repository.get_fact(fact_id)
    if fact.project_id != project_id:
        raise ValueError("fact 不属于当前 project")
    return svc.confirm(
        fact_id=fact_id, request=body, idempotency_key=key, actor=actor
    )


@router.post(
    "/{project_id}/facts/{fact_id}/correct",
    response_model=ProjectFactCorrectionResponse,
)
def correct_fact(
    project_id: str,
    fact_id: str,
    body: FactCorrectRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    fact = svc.repository.get_fact(fact_id)
    if fact.project_id != project_id:
        raise ValueError("fact 不属于当前 project")
    return svc.correct(
        fact_id=fact_id, request=body, idempotency_key=key, actor=actor
    )


@router.post(
    "/{project_id}/facts/{fact_id}/revoke",
    response_model=ProjectFactMutationResponse,
)
def revoke_fact(
    project_id: str,
    fact_id: str,
    body: FactTerminalRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    fact = svc.repository.get_fact(fact_id)
    if fact.project_id != project_id:
        raise ValueError("fact 不属于当前 project")
    return svc.revoke(
        fact_id=fact_id, request=body, idempotency_key=key, actor=actor
    )


@router.post(
    "/{project_id}/facts/{fact_id}/delete",
    response_model=ProjectFactMutationResponse,
)
def delete_fact(
    project_id: str,
    fact_id: str,
    body: FactTerminalRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
):
    fact = svc.repository.get_fact(fact_id)
    if fact.project_id != project_id:
        raise ValueError("fact 不属于当前 project")
    return svc.delete(
        fact_id=fact_id, request=body, idempotency_key=key, actor=actor
    )
