from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import require_api_auth
from app.resources.errors import (
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceKind,
    ResourceRequest,
)
from app.resources.service import (
    ResourceService,
    sanitize_resource_view,
)

router = APIRouter(prefix="/v1/resources")


class ResourceSubmitBody(BaseModel):
    """HTTP 提交体；第一版 submit 结果都是 awaiting_approval。"""

    model_config = ConfigDict(extra="forbid")

    kind: ResourceKind
    source_url: str = Field(min_length=1, max_length=2048)
    expected_sha256: str | None = None
    expected_git_commit: str | None = None
    purpose: str = Field(min_length=1, max_length=500)


class ResourceDecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern=r"^(approved|rejected)$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str | None = Field(default=None, max_length=500)
    expected_version: int | None = Field(default=None, ge=0)


class CancelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        default="user requested cancellation",
        min_length=1,
        max_length=500,
    )
    expected_version: int | None = Field(default=None, ge=0)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: str
    idempotency_key: str
    kind: ResourceKind
    source_url_sanitized: str
    purpose: str
    expected_sha256: str | None = None
    expected_git_commit: str | None = None
    request_sha256: str
    status: str
    version: int
    attempt_count: int
    worker_id: str | None = None
    approval: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class ResourceMutationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource: ResourceResponse
    replayed: bool | None = None


class EventView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: int
    resource_id: str
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class EventPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EventView]
    count: int


Actor = Annotated[str, Depends(require_api_auth)]

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=300,
    ),
]


def resource_service(request: Request) -> ResourceService:
    service = getattr(
        request.app.state, "resource_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RESOURCE_SERVICE_UNAVAILABLE",
                "message": "Resource service 未配置",
            },
        )
    return service


ResourceServiceDependency = Annotated[
    ResourceService, Depends(resource_service)
]


def _to_response(
    record,
    *,
    replayed: bool | None = None,
) -> ResourceMutationResponse:
    view = sanitize_resource_view(record)
    return ResourceMutationResponse(
        resource=ResourceResponse(**view),
        replayed=replayed,
    )


def _decided_at() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post(
    "",
    response_model=ResourceMutationResponse,
    status_code=201,
)
def submit_resource(
    body: ResourceSubmitBody,
    idempotency_key: IdempotencyKey,
    _actor: Actor,
    service: ResourceServiceDependency,
) -> ResourceMutationResponse:
    try:
        request = ResourceRequest(
            kind=body.kind,
            source_url=body.source_url,
            expected_sha256=body.expected_sha256,
            expected_git_commit=body.expected_git_commit,
            purpose=body.purpose,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_RESOURCE_REQUEST",
                "message": str(exc),
            },
        ) from exc
    try:
        record, created = service.submit(
            request=request,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_IDEMPOTENCY_KEY",
                "message": str(exc),
            },
        ) from exc
    return _to_response(record, replayed=not created)


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
)
def get_resource(
    resource_id: str,
    _actor: Actor,
    service: ResourceServiceDependency,
) -> ResourceResponse:
    try:
        record = service.get(resource_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    return ResourceResponse(
        **sanitize_resource_view(record)
    )


@router.get(
    "/{resource_id}/events",
    response_model=EventPage,
)
def list_resource_events(
    resource_id: str,
    _actor: Actor,
    service: ResourceServiceDependency,
    limit: int = 100,
) -> EventPage:
    try:
        events = service.events(resource_id, limit=limit)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    items = [
        EventView(
            event_id=event.event_id,
            resource_id=event.resource_id,
            event_type=event.event_type,
            actor=event.actor,
            payload=event.payload,
            created_at=event.created_at,
        )
        for event in events
    ]
    return EventPage(items=items, count=len(items))


@router.post(
    "/{resource_id}/decision",
    response_model=ResourceMutationResponse,
)
def submit_decision(
    resource_id: str,
    body: ResourceDecisionBody,
    _actor: Actor,
    service: ResourceServiceDependency,
) -> ResourceMutationResponse:
    approval = ResourceApproval(
        decision=body.decision,  # type: ignore[arg-type]
        request_sha256=body.request_sha256,
        decided_by=_actor,
        decided_at=_decided_at(),
        reason=body.reason,
    )
    try:
        record = service.approve(
            resource_id=resource_id,
            approval=approval,
            expected_version=body.expected_version,
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    except ResourceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESOURCE_CONFLICT",
                "message": str(exc),
            },
        ) from exc
    return _to_response(record, replayed=False)


@router.post(
    "/{resource_id}/cancel",
    response_model=ResourceMutationResponse,
)
def cancel_resource(
    resource_id: str,
    body: CancelBody,
    _actor: Actor,
    service: ResourceServiceDependency,
) -> ResourceMutationResponse:
    try:
        record = service.cancel(
            resource_id=resource_id,
            reason=body.reason,
            actor=_actor,
            expected_version=body.expected_version,
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    except ResourceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESOURCE_CONFLICT",
                "message": str(exc),
            },
        ) from exc
    return _to_response(record, replayed=False)
