import pytest

from app.knowledge_base.errors import KnowledgeConflictError
from app.knowledge_base.identity import sha256_value
from app.knowledge_base.repository import SqliteKnowledgeRepository
from tests.helpers.knowledge_base import (
    ingest_batch,
    make_graph_batch,
)


def test_ingestion_is_transactional_and_idempotent(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    batch = make_graph_batch(
        job_id="job-a",
        paper_name="Paper A",
        concept_name="PST convolution",
    )
    first, first_replayed = ingest_batch(repository, batch, key="ingest-a")
    second, second_replayed = ingest_batch(repository, batch, key="ingest-a")
    assert first_replayed is False
    assert second_replayed is True
    assert first == second
    assert first.created_entity_count == 2


def test_same_key_with_different_snapshot_is_rejected(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    first = make_graph_batch(
        job_id="job-a",
        paper_name="Paper A",
        concept_name="PST convolution",
    )
    second = make_graph_batch(
        job_id="job-b",
        paper_name="Paper B",
        concept_name="P4D convolution",
    )
    ingest_batch(repository, first, key="same-key")
    with pytest.raises(KnowledgeConflictError):
        ingest_batch(repository, second, key="same-key")


def test_archive_removes_active_job_reference(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    batch = make_graph_batch(
        job_id="job-a",
        paper_name="Paper A",
        concept_name="PST convolution",
    )
    record, _ = ingest_batch(repository, batch, key="ingest-a")
    assert repository.active_referenced_job_ids() == {"job-a"}
    repository.archive_ingestion(
        ingestion_id=record.ingestion_id,
        actor="test",
        reason="fixture cleanup",
        idempotency_key="archive-a",
        request_hash=sha256_value({"archive": record.ingestion_id}),
    )
    assert repository.active_referenced_job_ids() == set()
