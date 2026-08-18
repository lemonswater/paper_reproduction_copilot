from app.chat.context import ChatContextBuilder
from app.chat.schemas import ChatCitation
from app.knowledge_base.repository import SqliteKnowledgeRepository
from app.knowledge_base.retrieval import KnowledgeRetriever
from tests.helpers.knowledge_base import ingest_batch, make_graph_batch


def test_chat_source_binds_pack_subject_and_evidence(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    ingest_batch(
        repository,
        make_graph_batch(
            job_id="job-a",
            paper_name="PSTNet",
            concept_name="PST convolution",
        ),
        key="ingest-a",
    )
    builder = ChatContextBuilder(
        interaction=None,  # type: ignore[arg-type]
        artifact_catalog=None,  # type: ignore[arg-type]
        artifacts_to_open=1,
        source_limit=8,
        artifact_max_bytes=4096,
        total_context_chars=20000,
        log_max_bytes=4096,
        knowledge_retriever=KnowledgeRetriever(repository),
    )
    sources = builder._knowledge_sources(
        question="PST convolution 是什么",
        keywords={"pst", "convolution"},
    )
    assert sources
    citation = sources[0].citation
    assert citation.source_type == "knowledge"
    assert citation.knowledge_pack_hash is not None
    assert citation.knowledge_subject_id is not None
    assert citation.knowledge_evidence_ref_ids


def test_non_knowledge_citation_rejects_knowledge_identity():
    try:
        ChatCitation(
            citation_id="job:current",
            source_type="job",
            label="job",
            knowledge_pack_hash="a" * 64,
            knowledge_subject_id="kgent_" + "1" * 24,
            knowledge_subject_hash="b" * 64,
            knowledge_evidence_ref_ids=["kgev_" + "1" * 24],
        )
    except ValueError:
        return
    raise AssertionError("非 knowledge citation 不应接受 Knowledge identity")
