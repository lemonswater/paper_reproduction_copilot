from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.api.auth import require_api_auth
from app.knowledge_base.schemas import (
    KnowledgeArchiveRequest,
    KnowledgeEquivalenceProposalRequest,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeIngestionRecord,
    KnowledgeQueryPack,
    KnowledgeQueryRequest,
    KnowledgeRelationMutationResponse,
    KnowledgeRelationRecord,
    KnowledgeRelationReviewRequest,
)
from app.knowledge_base.service import KnowledgeService


router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])
Actor = Annotated[str, Depends(require_api_auth)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=300),
]


def knowledge_service(request: Request) -> KnowledgeService:
    service = getattr(request.app.state, "knowledge_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Knowledge Base 未启用")
    return service


Service = Annotated[KnowledgeService, Depends(knowledge_service)]


@router.post("/ingestions", response_model=KnowledgeIngestResponse)
def ingest_job(
    body: KnowledgeIngestRequest,
    key: IdempotencyKey,
    actor: Actor,
    service: Service,
) -> KnowledgeIngestResponse:
    return service.ingest(
        job_id=body.job_id,
        actor=actor,
        idempotency_key=key,
    )


@router.post("/query", response_model=KnowledgeQueryPack)
def query_knowledge(
    body: KnowledgeQueryRequest,
    actor: Actor,
    service: Service,
) -> KnowledgeQueryPack:
    del actor
    return service.query(body)


@router.get(
    "/relations/candidates",
    response_model=list[KnowledgeRelationRecord],
)
def list_candidates(
    actor: Actor,
    service: Service,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[KnowledgeRelationRecord]:
    del actor
    return service.repository.list_candidate_relations(limit=limit)


@router.post(
    "/relations/equivalence",
    response_model=KnowledgeRelationMutationResponse,
)
def propose_equivalence(
    body: KnowledgeEquivalenceProposalRequest,
    key: IdempotencyKey,
    actor: Actor,
    service: Service,
) -> KnowledgeRelationMutationResponse:
    del actor
    return service.propose_equivalence(
        request=body,
        idempotency_key=key,
    )


@router.post(
    "/relations/{relation_id}/review",
    response_model=KnowledgeRelationMutationResponse,
)
def review_relation(
    relation_id: str,
    body: KnowledgeRelationReviewRequest,
    key: IdempotencyKey,
    actor: Actor,
    service: Service,
) -> KnowledgeRelationMutationResponse:
    return service.review_relation(
        relation_id=relation_id,
        request=body,
        actor=actor,
        idempotency_key=key,
    )


@router.post(
    "/ingestions/{ingestion_id}/archive",
    response_model=KnowledgeIngestionRecord,
)
def archive_ingestion(
    ingestion_id: str,
    body: KnowledgeArchiveRequest,
    key: IdempotencyKey,
    actor: Actor,
    service: Service,
) -> KnowledgeIngestionRecord:
    return service.archive_ingestion(
        ingestion_id=ingestion_id,
        actor=actor,
        reason=body.reason,
        idempotency_key=key,
    )
