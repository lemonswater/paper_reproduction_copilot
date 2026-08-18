from app.knowledge_base.repository import SqliteKnowledgeRepository
from tests.helpers.knowledge_base import ingest_batch, make_graph_batch


def test_active_ingestion_holds_source_job(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    ingest_batch(
        repository,
        make_graph_batch(
            job_id="job-held",
            paper_name="Paper Held",
            concept_name="Point tube convolution",
        ),
        key="ingest-held",
    )
    assert repository.active_referenced_job_ids() == {"job-held"}
