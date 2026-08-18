from app.knowledge_base.repository import SqliteKnowledgeRepository
from app.knowledge_base.retrieval import KnowledgeRetriever
from app.knowledge_base.schemas import KnowledgeQueryRequest
from tests.helpers.knowledge_base import ingest_batch, make_graph_batch


def test_cross_paper_query_returns_evidence_without_candidates(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    ingest_batch(
        repository,
        make_graph_batch(
            job_id="job-a",
            paper_name="PSTNet",
            concept_name="PST convolution",
            dataset_name="MSR-Action3D",
        ),
        key="ingest-a",
    )
    ingest_batch(
        repository,
        make_graph_batch(
            job_id="job-b",
            paper_name="P4Transformer",
            concept_name="P4D convolution",
        ),
        key="ingest-b",
    )
    pack = KnowledgeRetriever(repository).query(
        KnowledgeQueryRequest(
            query="convolution",
            entity_kinds=["concept_instance"],
            max_depth=0,
        )
    )
    assert {item.entity.display_name for item in pack.entities} == {
        "PST convolution",
        "P4D convolution",
    }
    assert pack.candidate_relations == []
    assert pack.evidence_refs
    assert pack.subject_evidence
