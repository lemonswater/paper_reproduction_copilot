import pytest

from app.knowledge_base.errors import KnowledgeConflictError
from app.knowledge_base.repository import SqliteKnowledgeRepository
from app.knowledge_base.retrieval import KnowledgeRetriever
from app.knowledge_base.schemas import (
    KnowledgeEquivalenceProposalRequest,
    KnowledgeRelationReviewRequest,
)
from app.knowledge_base.service import KnowledgeService
from tests.helpers.knowledge_base import ingest_batch, make_graph_batch


def _service(repository):
    return KnowledgeService(
        repository=repository,
        source_reader=None,  # type: ignore[arg-type]
        projector=None,  # type: ignore[arg-type]
        retriever=KnowledgeRetriever(repository),
        minimum_equivalence_score=0.65,
    )


def test_equivalence_requires_review_and_rejects_stale(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    first = make_graph_batch(
        job_id="job-a",
        paper_name="Paper A",
        concept_name="Temporal convolution",
    )
    second = make_graph_batch(
        job_id="job-b",
        paper_name="Paper B",
        concept_name="Temporal convolution",
    )
    ingest_batch(repository, first, key="ingest-a")
    ingest_batch(repository, second, key="ingest-b")
    concepts = repository.search_entities(
        terms=["temporal", "convolution"],
        kinds=["concept_instance"],
        limit=10,
    )
    assert len(concepts) == 2
    service = _service(repository)
    proposed = service.propose_equivalence(
        request=KnowledgeEquivalenceProposalRequest(
            source_entity_id=concepts[0].entity_id,
            target_entity_id=concepts[1].entity_id,
            expected_source_hash=concepts[0].record_hash,
            expected_target_hash=concepts[1].record_hash,
            reason="same normalized method name across two papers",
        ),
        idempotency_key="proposal-a-b",
    )
    assert proposed.relation.status == "candidate"
    old_hash = proposed.relation.relation_hash
    confirmed = service.review_relation(
        relation_id=proposed.relation.relation_id,
        request=KnowledgeRelationReviewRequest(
            decision="confirmed",
            expected_version=0,
            expected_relation_hash=old_hash,
            reason="checked both paper evidence records",
        ),
        actor="test:user",
        idempotency_key="confirm-a-b",
    )
    assert confirmed.relation.status == "confirmed"
    assert confirmed.relation.version == 1

    replay = service.review_relation(
        relation_id=proposed.relation.relation_id,
        request=KnowledgeRelationReviewRequest(
            decision="confirmed",
            expected_version=0,
            expected_relation_hash=old_hash,
            reason="checked both paper evidence records",
        ),
        actor="test:user",
        idempotency_key="confirm-a-b",
    )
    assert replay.replayed is True
    assert replay.relation == confirmed.relation

    with pytest.raises(KnowledgeConflictError):
        service.review_relation(
            relation_id=proposed.relation.relation_id,
            request=KnowledgeRelationReviewRequest(
                decision="rejected",
                expected_version=0,
                expected_relation_hash=old_hash,
                reason="stale browser tab",
            ),
            actor="test:user",
            idempotency_key="stale-review",
        )
