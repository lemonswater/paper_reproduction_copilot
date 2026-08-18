import pytest
from pydantic import ValidationError

from app.knowledge_base.schemas import (
    KnowledgeEvidenceRef,
    KnowledgeRelationRecord,
)
from tests.helpers.knowledge_base import NOW


def test_paper_evidence_requires_paper_identity():
    with pytest.raises(ValidationError):
        KnowledgeEvidenceRef(
            evidence_ref_id="kgev_" + "1" * 24,
            kind="paper_artifact",
            job_id="job-a",
            run_id="run-a",
            artifact_id="artifact-a",
            artifact_path="analysis/paper_fact_index.json",
            artifact_sha256="a" * 64,
            content_hash="b" * 64,
        )


def test_candidate_requires_proposal_reason():
    with pytest.raises(ValidationError):
        KnowledgeRelationRecord(
            relation_id="kgrel_" + "1" * 24,
            relation_type="equivalent_to",
            source_entity_id="kgent_" + "1" * 24,
            target_entity_id="kgent_" + "2" * 24,
            status="candidate",
            authority="deterministic_similarity",
            confidence=0.8,
            relation_hash="a" * 64,
            version=0,
            created_at=NOW,
            updated_at=NOW,
        )
