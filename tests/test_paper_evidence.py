from __future__ import annotations

import hashlib

import pytest

from app.paper.evidence import (
    InvalidEvidenceReference,
    resolve_evidence,
    validate_extraction_evidence_references,
)
from app.paper.schemas import (
    EvidenceDraft,
    MethodModuleDraft,
    PaperBlock,
    PaperDocument,
    PaperSection,
    SectionExtractionDraft,
    SectionChunk,
)


def _fixture():
    text = "We train all networks for 35 epochs."
    block = PaperBlock(
        block_id="p014-b0007",
        page=14,
        order=7,
        block_type="paragraph",
        text=text,
        text_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    section = PaperSection(
        section_id="sec-impl",
        number="C",
        title="Implementation Details",
        normalized_title="implementation details",
        level=1,
        kind="implementation",
        page_start=14,
        page_end=14,
        block_ids=[block.block_id],
        content_hash="section-hash",
    )
    chunk = SectionChunk(
        chunk_id="sec-impl-c000",
        section_id=section.section_id,
        section_title=section.title,
        section_kind=section.kind,
        page_start=14,
        page_end=14,
        block_ids=[block.block_id],
        text=f"[{block.block_id}][page 14] {text}",
        content_hash="chunk-hash",
    )
    document = PaperDocument(
        document_id="paper-pstnet",
        source_path="pdf/pstnet.pdf",
        source_sha256="source-hash",
        parser_version="phase18-v1",
        page_count=23,
        indexed_page_count=23,
        block_count=1,
        section_count=1,
        blocks_artifact="analysis/paper_blocks.json",
        sections_artifact="analysis/paper_sections.json",
        parse_report_artifact="analysis/paper_parse_report.json",
    )
    return block, section, chunk, document


def test_resolver_computes_page_and_hash_from_block() -> None:
    block, section, chunk, document = _fixture()

    resolved = resolve_evidence(
        draft=EvidenceDraft(
            block_ids=[block.block_id],
            summary="All networks are trained for 35 epochs.",
            confidence=0.99,
        ),
        document=document,
        section=section,
        chunk=chunk,
        blocks_by_id={block.block_id: block},
    )

    assert resolved.page_start == 14
    assert resolved.section_id == "sec-impl"
    assert resolved.content_hash == hashlib.sha256(
        block.text.encode()
    ).hexdigest()


def test_resolver_rejects_unknown_block_id() -> None:
    block, section, chunk, document = _fixture()

    with pytest.raises(InvalidEvidenceReference):
        resolve_evidence(
            draft=EvidenceDraft(
                block_ids=["invented-block"],
                summary="Invented evidence.",
            ),
            document=document,
            section=section,
            chunk=chunk,
            blocks_by_id={block.block_id: block},
        )


def test_resolver_restores_unique_block_hash_in_current_chunk() -> None:
    block, section, chunk, document = _fixture()
    block = block.model_copy(
        update={"block_id": "p014-b0007-0123456789"}
    )
    section = section.model_copy(update={"block_ids": [block.block_id]})
    chunk = chunk.model_copy(update={"block_ids": [block.block_id]})

    resolved = resolve_evidence(
        draft=EvidenceDraft(
            block_ids=["p014-b0007-deadbeef00"],
            summary="All networks are trained for 35 epochs.",
        ),
        document=document,
        section=section,
        chunk=chunk,
        blocks_by_id={block.block_id: block},
    )

    assert resolved.block_ids == [block.block_id]


def test_extraction_validation_persists_canonical_block_id() -> None:
    block, _, chunk, _ = _fixture()
    block = block.model_copy(
        update={"block_id": "p014-b0007-0123456789"}
    )
    chunk = chunk.model_copy(update={"block_ids": [block.block_id]})
    extraction = SectionExtractionDraft(
        section_id=chunk.section_id,
        chunk_id=chunk.chunk_id,
        summary="Implementation details",
        method_modules=[
            MethodModuleDraft(
                name="PST convolution",
                description="Spatio-temporal feature extraction.",
                evidence=EvidenceDraft(
                    block_ids=["p014-b0007"],
                    summary="PST convolution definition.",
                ),
            )
        ],
    )

    validate_extraction_evidence_references(
        extraction=extraction,
        chunk=chunk,
        blocks_by_id={block.block_id: block},
    )

    assert extraction.method_modules[0].evidence.block_ids == [
        block.block_id
    ]


def test_resolver_does_not_restore_block_from_outside_chunk() -> None:
    block, section, chunk, document = _fixture()
    outside = block.model_copy(
        update={"block_id": "p015-b0008-abcdef0123", "page": 15}
    )

    with pytest.raises(InvalidEvidenceReference):
        resolve_evidence(
            draft=EvidenceDraft(
                block_ids=["p015-b0008"],
                summary="Outside evidence.",
            ),
            document=document,
            section=section,
            chunk=chunk,
            blocks_by_id={
                block.block_id: block,
                outside.block_id: outside,
            },
        )
