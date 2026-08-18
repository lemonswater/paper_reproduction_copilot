from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import require_api_auth
from app.research_browser.schemas import (
    ResearchEvidencePack,
    ResearchEvent,
    ResearchPublicRecord,
    ResearchRequest,
    ResearchResourceLinkResponse,
    ResearchResourceSelection,
)
from app.research_browser.service import ResearchBrowserService


router = APIRouter(
    prefix="/v1/research",
    tags=["research-browser"],
)
Actor = Annotated[str, Depends(require_api_auth)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=300),
]


class ResearchRunBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)


class ResearchCancelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)


def service(request: Request) -> ResearchBrowserService:
    selected = getattr(request.app.state, "research_browser_service", None)
    if selected is None:
        # Disabled 路由通常不会注册；保留此检查防止测试注入错误。
        raise RuntimeError("RESEARCH_BROWSER_DISABLED")
    return selected


Service = Annotated[ResearchBrowserService, Depends(service)]


@router.post("", response_model=ResearchPublicRecord)
def submit_research(
    body: ResearchRequest,
    key: IdempotencyKey,
    actor: Actor,
    svc: Service,
) -> ResearchPublicRecord:
    record = svc.submit(
        request=body,
        idempotency_key=key,
        actor=actor,
    )
    return ResearchPublicRecord.from_record(record)


@router.post("/{research_id}/run", response_model=ResearchPublicRecord)
def run_research(
    research_id: str,
    body: ResearchRunBody,
    actor: Actor,
    svc: Service,
) -> ResearchPublicRecord:
    record = svc.run(
        session_id=research_id,
        expected_version=body.expected_version,
        actor=actor,
    )
    return ResearchPublicRecord.from_record(record)


@router.get("/{research_id}", response_model=ResearchPublicRecord)
def get_research(
    research_id: str,
    actor: Actor,
    svc: Service,
) -> ResearchPublicRecord:
    del actor
    return ResearchPublicRecord.from_record(svc.get(research_id))


@router.get(
    "/{research_id}/pack",
    response_model=ResearchEvidencePack,
)
def get_pack(
    research_id: str,
    actor: Actor,
    svc: Service,
) -> ResearchEvidencePack:
    del actor
    return svc.get_pack(research_id)


@router.get(
    "/{research_id}/events",
    response_model=list[ResearchEvent],
)
def list_events(
    research_id: str,
    actor: Actor,
    svc: Service,
    after_event_id: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ResearchEvent]:
    del actor
    return svc.events(
        research_id,
        after_event_id=after_event_id,
        limit=limit,
    )


@router.post("/{research_id}/cancel", response_model=ResearchPublicRecord)
def cancel_research(
    research_id: str,
    body: ResearchCancelBody,
    actor: Actor,
    svc: Service,
) -> ResearchPublicRecord:
    record = svc.cancel(
        session_id=research_id,
        expected_version=body.expected_version,
        actor=actor,
    )
    return ResearchPublicRecord.from_record(record)


@router.post(
    "/{research_id}/resource-candidates",
    response_model=ResearchResourceLinkResponse,
)
def request_resource_candidate(
    research_id: str,
    body: ResearchResourceSelection,
    actor: Actor,
    svc: Service,
) -> ResearchResourceLinkResponse:
    # Resource Bridge 使用服务端候选身份派生稳定幂等键。
    resource = svc.submit_resource_candidate(
        session_id=research_id,
        selection=body,
        actor=actor,
    )
    return ResearchResourceLinkResponse(
        session_id=research_id,
        candidate_id=body.candidate_id,
        resource_id=resource.resource_id,
        resource_request_sha256=resource.request_sha256,
        resource_status=resource.status,
        resource_version=resource.version,
    )
