from pathlib import Path

from app.knowledge_base.evaluation import (
    evaluate_knowledge_cases,
    load_knowledge_golden_cases,
)
from app.knowledge_base.repository import SqliteKnowledgeRepository
from app.knowledge_base.retrieval import KnowledgeRetriever
from tests.helpers.knowledge_base import ingest_batch, make_graph_batch


def test_cross_paper_offline_golden_suite(tmp_path):
    repository = SqliteKnowledgeRepository(tmp_path / "knowledge.sqlite")
    repository.initialize()
    ingest_batch(
        repository,
        make_graph_batch(
            job_id="job-pst",
            paper_name="PSTNet",
            concept_name="PST convolution",
            dataset_name="MSR-Action3D",
        ),
        key="ingest-pst",
    )
    ingest_batch(
        repository,
        make_graph_batch(
            job_id="job-p4d",
            paper_name="P4Transformer",
            concept_name="P4D convolution",
        ),
        key="ingest-p4d",
    )
    suite_id, cases = load_knowledge_golden_cases(
        Path(
            "app/evaluation/knowledge_cases/"
            "cross_paper_offline_v1.json"
        )
    )
    report = evaluate_knowledge_cases(
        retriever=KnowledgeRetriever(repository),
        suite_id=suite_id,
        cases=cases,
    )
    assert report.passed is True
    assert report.passed_count == report.case_count == 2
