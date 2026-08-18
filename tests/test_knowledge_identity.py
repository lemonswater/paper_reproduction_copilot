import pytest

from app.knowledge_base.identity import (
    build_entity_id,
    build_relation_id,
    normalize_knowledge_key,
    reviewed_relation,
)
from tests.helpers.knowledge_base import _relation


def test_entity_identity_is_source_scoped():
    canonical = normalize_knowledge_key("PST Convolution")
    first = build_entity_id(
        kind="concept_instance",
        scope_key="paper-a",
        canonical_key=canonical,
    )
    second = build_entity_id(
        kind="concept_instance",
        scope_key="paper-b",
        canonical_key=canonical,
    )
    assert first != second


def test_equivalence_relation_identity_is_symmetric():
    first = build_relation_id(
        relation_type="equivalent_to",
        source_entity_id="kgent_" + "1" * 24,
        target_entity_id="kgent_" + "2" * 24,
    )
    second = build_relation_id(
        relation_type="equivalent_to",
        source_entity_id="kgent_" + "2" * 24,
        target_entity_id="kgent_" + "1" * 24,
    )
    assert first == second


def test_asserted_relation_cannot_be_reviewed_as_candidate():
    relation = _relation(
        relation_type="paper_uses_dataset",
        source="kgent_" + "1" * 24,
        target="kgent_" + "2" * 24,
    )
    with pytest.raises(ValueError):
        reviewed_relation(
            relation,
            decision="confirmed",
            actor="test",
            reason="not a candidate",
        )
