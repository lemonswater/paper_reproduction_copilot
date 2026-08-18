from __future__ import annotations

import pytest

from app.paper.evidence import to_legacy_evidence
from app.paper.schemas import PaperEvidence


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (0.0, "low"),
        (0.59, "low"),
        (0.60, "medium"),
        (0.84, "medium"),
        (0.85, "high"),
        (1.0, "high"),
    ],
)
def test_legacy_evidence_maps_numeric_confidence(
    confidence: float,
    expected: str,
) -> None:
    paper_evidence = PaperEvidence(
        evidence_id="pev-confidence",
        document_id="paper-test",
        section_id="sec-test",
        block_ids=["block-test"],
        page_start=1,
        page_end=1,
        text="Evidence text.",
        summary="Evidence summary.",
        content_hash="a" * 64,
        confidence=confidence,
    )

    legacy = to_legacy_evidence(
        paper_evidence,
        source_path="paper.pdf",
        section_title="Experiments",
    )

    assert legacy.confidence == expected
