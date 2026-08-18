from app.knowledge_base.projector import KnowledgeProjector
from app.knowledge_base.source_reader import KnowledgeSourceReader
from tests.helpers.knowledge_base import (
    FakeVerifiedRuns,
    make_source_fixture,
)


def test_projector_builds_paper_section_claim_and_concept():
    evidence, catalog = make_source_fixture()
    reader = KnowledgeSourceReader(
        verified_runs=FakeVerifiedRuns(evidence),
        artifact_catalog=catalog,
        max_artifact_bytes=2 * 1024 * 1024,
        max_sections=100,
        max_facts=100,
        max_mappings=100,
    )
    batch = KnowledgeProjector().project(reader.read("job-a"))
    kinds = {item.kind for item in batch.entities}
    relation_types = {item.relation_type for item in batch.relations}
    assert {"paper", "section", "claim", "concept_instance"} <= kinds
    assert "paper_has_section" in relation_types
    assert "section_supports_claim" in relation_types
    assert "claim_describes_concept" in relation_types
    assert {
        item.subject_id for item in batch.provenance
    } == {
        *[item.entity_id for item in batch.entities],
        *[item.relation_id for item in batch.relations],
    }
