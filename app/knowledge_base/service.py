from __future__ import annotations

from app.knowledge_base.errors import (
    KnowledgeConflictError,
    KnowledgeIntegrityError,
)
from app.knowledge_base.identity import (
    build_provenance_id,
    build_relation_id,
    graph_batch_hash,
    provenance_record_hash,
    relation_record_hash,
    reviewed_relation,
    sha256_value,
    utc_now,
)
from app.knowledge_base.ports import KnowledgeRepository
from app.knowledge_base.projector import KnowledgeProjector
from app.knowledge_base.retrieval import (
    KnowledgeRetriever,
    entity_similarity,
)
from app.knowledge_base.schemas import (
    KnowledgeEquivalenceProposalRequest,
    KnowledgeIngestionRecord,
    KnowledgeIngestResponse,
    KnowledgeProvenanceRecord,
    KnowledgeQueryPack,
    KnowledgeQueryRequest,
    KnowledgeRelationMutationResponse,
    KnowledgeRelationRecord,
    KnowledgeRelationReviewRequest,
)
from app.knowledge_base.source_reader import KnowledgeSourceReader


EQUIVALENCE_KINDS = {
    "concept_instance",
    "dataset_mention",
    "metric_mention",
}


class KnowledgeService:
    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        source_reader: KnowledgeSourceReader,
        projector: KnowledgeProjector,
        retriever: KnowledgeRetriever,
        minimum_equivalence_score: float,
    ) -> None:
        self.repository = repository
        self.source_reader = source_reader
        self.projector = projector
        self.retriever = retriever
        self.minimum_equivalence_score = minimum_equivalence_score

    def ingest(
        self,
        *,
        job_id: str,
        actor: str,
        idempotency_key: str,
    ) -> KnowledgeIngestResponse:
        bundle = self.source_reader.read(job_id)
        batch = self.projector.project(bundle)
        batch_hash = graph_batch_hash(batch)
        request_hash = sha256_value(
            {
                "operation": "knowledge_ingest",
                "job_id": job_id,
                "snapshot_hash": batch.source.snapshot_hash,
                "batch_hash": batch_hash,
                "actor": actor,
            }
        )
        ingestion = KnowledgeIngestionRecord(
            ingestion_id=(
                "kging_"
                f"{sha256_value({'snapshot': batch.source.snapshot_hash})[:24]}"
            ),
            source=batch.source,
            status="active",
            entity_count=0,
            relation_count=0,
            created_entity_count=0,
            created_relation_count=0,
            batch_hash=batch_hash,
            request_hash=request_hash,
            created_by=actor,
            created_at=utc_now(),
        )
        stored, replayed = self.repository.ingest_batch(
            batch=batch,
            ingestion=ingestion,
            idempotency_key=idempotency_key,
        )
        return KnowledgeIngestResponse(
            ingestion=stored,
            replayed=replayed,
        )

    def query(self, request: KnowledgeQueryRequest) -> KnowledgeQueryPack:
        return self.retriever.query(request)

    def propose_equivalence(
        self,
        *,
        request: KnowledgeEquivalenceProposalRequest,
        idempotency_key: str,
    ) -> KnowledgeRelationMutationResponse:
        source = self.repository.get_entity(request.source_entity_id)
        target = self.repository.get_entity(request.target_entity_id)
        if (
            source.record_hash != request.expected_source_hash
            or target.record_hash != request.expected_target_hash
        ):
            raise KnowledgeConflictError("Entity Hash 已变化")
        if source.kind != target.kind or source.kind not in EQUIVALENCE_KINDS:
            raise KnowledgeConflictError(
                "只有同类 concept/dataset/metric Entity 可提议等价"
            )
        if source.scope_key == target.scope_key:
            raise KnowledgeConflictError("同一 source scope 不创建跨源等价候选")

        score, _ = entity_similarity(source.display_name, target)
        if score < self.minimum_equivalence_score:
            raise KnowledgeConflictError(
                f"确定性相似度不足：{score:.4f}"
            )
        source_id, target_id = sorted(
            [source.entity_id, target.entity_id]
        )
        now = utc_now()
        draft = KnowledgeRelationRecord(
            relation_id=build_relation_id(
                relation_type="equivalent_to",
                source_entity_id=source_id,
                target_entity_id=target_id,
            ),
            relation_type="equivalent_to",
            source_entity_id=source_id,
            target_entity_id=target_id,
            status="candidate",
            authority="deterministic_similarity",
            confidence=score,
            relation_hash="0" * 64,
            version=0,
            created_at=now,
            updated_at=now,
            proposal_reason=request.reason.strip(),
        )
        relation = draft.model_copy(
            update={"relation_hash": relation_record_hash(draft)}
        )

        entity_provenance = self.repository.provenance_for_subjects(
            subject_ids=[source.entity_id, target.entity_id],
            limit=100,
        )
        covered = {item.subject_id for item in entity_provenance}
        if covered != {source.entity_id, target.entity_id}:
            raise KnowledgeIntegrityError(
                "等价候选端点缺少活动 Provenance"
            )
        relation_provenance = []
        for item in entity_provenance:
            candidate = KnowledgeProvenanceRecord(
                provenance_id=build_provenance_id(
                    subject_id=relation.relation_id,
                    source_snapshot_id=item.source_snapshot_id,
                    evidence_ref_ids=[
                        ref.evidence_ref_id for ref in item.evidence
                    ],
                ),
                subject_kind="relation",
                subject_id=relation.relation_id,
                source_snapshot_id=item.source_snapshot_id,
                authority="deterministic_similarity",
                evidence=item.evidence,
                provenance_hash="0" * 64,
                created_at=now,
            )
            relation_provenance.append(
                candidate.model_copy(
                    update={
                        "provenance_hash": provenance_record_hash(
                            candidate
                        )
                    }
                )
            )
        request_hash = sha256_value(
            {
                "operation": "knowledge_propose_equivalence",
                "request": request.model_dump(mode="json"),
                "relation_hash": relation.relation_hash,
            }
        )
        stored, replayed = self.repository.create_candidate_relation(
            relation=relation,
            provenance=relation_provenance,
            expected_entity_hashes={
                source.entity_id: source.record_hash,
                target.entity_id: target.record_hash,
            },
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        return KnowledgeRelationMutationResponse(
            relation=stored,
            replayed=replayed,
        )

    def review_relation(
        self,
        *,
        relation_id: str,
        request: KnowledgeRelationReviewRequest,
        actor: str,
        idempotency_key: str,
    ) -> KnowledgeRelationMutationResponse:
        request_hash = sha256_value(
            {
                "operation": "knowledge_review_relation",
                "relation_id": relation_id,
                "request": request.model_dump(mode="json"),
                "actor": actor,
            }
        )
        current = self.repository.get_relation(relation_id)
        if (
            current.version != request.expected_version
            or current.relation_hash != request.expected_relation_hash
        ):
            # 仍进入 Repository：同 Key/同 Request 先重放历史响应；
            # 没有重放记录时，Repository 才按 expected identity 返回 stale。
            stored, replayed = self.repository.replace_relation(
                relation=current,
                expected_version=request.expected_version,
                expected_hash=request.expected_relation_hash,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            return KnowledgeRelationMutationResponse(
                relation=stored,
                replayed=replayed,
            )
        try:
            updated = reviewed_relation(
                current,
                decision=request.decision,
                actor=actor,
                reason=request.reason,
            )
        except ValueError as exc:
            raise KnowledgeConflictError(str(exc)) from exc
        stored, replayed = self.repository.replace_relation(
            relation=updated,
            expected_version=request.expected_version,
            expected_hash=request.expected_relation_hash,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        return KnowledgeRelationMutationResponse(
            relation=stored,
            replayed=replayed,
        )

    def archive_ingestion(
        self,
        *,
        ingestion_id: str,
        actor: str,
        reason: str,
        idempotency_key: str,
    ) -> KnowledgeIngestionRecord:
        request_hash = sha256_value(
            {
                "operation": "knowledge_archive_ingestion",
                "ingestion_id": ingestion_id,
                "actor": actor,
                "reason": reason.strip(),
            }
        )
        record, _ = self.repository.archive_ingestion(
            ingestion_id=ingestion_id,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        return record
