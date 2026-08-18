"""Phase 31/36 Chat API routes。"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)

from app.api.auth import require_api_auth
from app.chat.errors import (
    ChatConflictError,
    ChatUnavailableError,
)
from app.chat.schemas import (
    ChatAskRequest,
    ChatAskResponse,
    ChatMessagePage,
    ConversationMemoryView,
)
from app.chat.service import ChatService
from app.config import settings

router = APIRouter(prefix="/v1/jobs/{job_id}/chat")
Actor = Annotated[str, Depends(require_api_auth)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=300,
    ),
]
AfterSequence = Annotated[int, Query(ge=0)]
PageLimit = Annotated[int, Query(ge=1)]


def chat_service(request: Request) -> ChatService:
    service = getattr(
        request.app.state,
        "chat_service",
        None,
    )
    if service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_DISABLED",
                "message": "Chat Agent 未启用",
            },
        )
    return service


ChatDependency = Annotated[
    ChatService,
    Depends(chat_service),
]


@router.get("", response_model=ChatMessagePage)
def list_chat_messages(
    job_id: str,
    _actor: Actor,
    service: ChatDependency,
    after: AfterSequence = 0,
    limit: PageLimit = 100,
) -> ChatMessagePage:
    return service.list_messages(
        job_id=job_id,
        after_sequence=after,
        limit=min(limit, settings.api_max_page_size),
    )


@router.get("/recent", response_model=ChatMessagePage)
def list_recent_chat_messages(
    job_id: str,
    _actor: Actor,
    service: ChatDependency,
    limit: PageLimit = 100,
) -> ChatMessagePage:
    return service.list_recent_messages(
        job_id=job_id,
        limit=min(limit, settings.api_max_page_size),
    )


@router.get(
    "/memory",
    response_model=Optional[ConversationMemoryView],
)
def get_chat_memory(
    job_id: str,
    _actor: Actor,
    service: ChatDependency,
) -> ConversationMemoryView | None:
    try:
        return service.get_memory(job_id=job_id)
    except ChatUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_MEMORY_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc


@router.post("", response_model=ChatAskResponse)
def ask_chat_agent(
    job_id: str,
    body: ChatAskRequest,
    idempotency_key: IdempotencyKey,
    _actor: Actor,
    service: ChatDependency,
) -> ChatAskResponse:
    try:
        return service.ask(
            job_id=job_id,
            question=body.question,
            idempotency_key=idempotency_key,
        )
    except ChatConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHAT_CONFLICT",
                "message": str(exc),
            },
        ) from exc
    except ChatUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_PROVIDER_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
