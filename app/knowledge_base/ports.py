from __future__ import annotations

from typing import Protocol

from app.knowledge_base.schemas import (
    KnowledgeEntityKind,
    KnowledgeEntityRecord,
    KnowledgeGraphBatch,
    KnowledgeIngestionRecord,
    KnowledgeProvenanceRecord,
    KnowledgeRelationRecord,
)


class KnowledgeRepository(Protocol):
    def initialize(self) -> None:
        ...

    def ingest_batch(
        self,
        *,
        batch: KnowledgeGraphBatch,
        ingestion: KnowledgeIngestionRecord,
        idempotency_key: str,
    ) -> tuple[KnowledgeIngestionRecord, bool]:
        ...

    def get_entity(self, entity_id: str) -> KnowledgeEntityRecord:
        ...

    def get_relation(self, relation_id: str) -> KnowledgeRelationRecord:
        ...

    def get_ingestion(self, ingestion_id: str) -> KnowledgeIngestionRecord:
        ...

    def list_candidate_relations(
        self,
        *,
        limit: int,
    ) -> list[KnowledgeRelationRecord]:
        ...

    def search_entities(
        self,
        *,
        terms: list[str],
        kinds: list[KnowledgeEntityKind],
        limit: int,
    ) -> list[KnowledgeEntityRecord]:
        ...

    def relations_for_entities(
        self,
        *,
        entity_ids: list[str],
        include_candidates: bool,
        limit: int,
    ) -> list[KnowledgeRelationRecord]:
        ...

    def active_entities_by_ids(
        self,
        *,
        entity_ids: list[str],
        limit: int,
    ) -> list[KnowledgeEntityRecord]:
        ...

    def provenance_for_subjects(
        self,
        *,
        subject_ids: list[str],
        limit: int,
    ) -> list[KnowledgeProvenanceRecord]:
        ...

    def create_candidate_relation(
        self,
        *,
        relation: KnowledgeRelationRecord,
        provenance: list[KnowledgeProvenanceRecord],
        expected_entity_hashes: dict[str, str],
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[KnowledgeRelationRecord, bool]:
        ...

    def replace_relation(
        self,
        *,
        relation: KnowledgeRelationRecord,
        expected_version: int,
        expected_hash: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[KnowledgeRelationRecord, bool]:
        ...

    def archive_ingestion(
        self,
        *,
        ingestion_id: str,
        actor: str,
        reason: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[KnowledgeIngestionRecord, bool]:
        ...

    def active_referenced_job_ids(self) -> set[str]:
        ...
