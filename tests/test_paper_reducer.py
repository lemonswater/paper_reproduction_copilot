from __future__ import annotations

from app.paper.reducer import (
    find_experiment_setting_conflicts,
    reduce_section_extractions,
)
from app.paper.schemas import (
    EvidenceDraft,
    ExperimentSettingDraft,
    NamedFactDraft,
    PaperBlock,
    PaperDocument,
    PaperEvidence,
    PaperFactRecord,
    PaperSection,
    SectionChunk,
    SectionExtractionDraft,
    TextFactDraft,
)


def _paper_objects():
    block = PaperBlock(
        block_id="p1-b0-aaaaaaaaaaaa",
        page=1,
        order=0,
        block_type="paragraph",
        text="We use NTU RGB+D with batch size 32.",
        text_hash="a" * 64,
    )
    section = PaperSection(
        section_id="sec-experiments",
        number="4",
        title="Experiments",
        normalized_title="experiments",
        level=1,
        kind="experiments",
        page_start=1,
        page_end=1,
        block_ids=[block.block_id],
        content_hash="b" * 64,
    )
    chunk = SectionChunk(
        chunk_id="chunk-experiments-0",
        section_id=section.section_id,
        section_title=section.title,
        section_kind=section.kind,
        page_start=1,
        page_end=1,
        block_ids=[block.block_id],
        text=f"[{block.block_id}][page 1] {block.text}",
        content_hash="c" * 64,
    )
    document = PaperDocument(
        document_id="paper-test",
        source_path="/data/tianshaoqi24/fixtures/paper.pdf",
        source_sha256="d" * 64,
        parser_version="phase18-v1",
        page_count=1,
        indexed_page_count=1,
        block_count=1,
        section_count=1,
        blocks_artifact="analysis/paper_blocks.json",
        sections_artifact="analysis/paper_sections.json",
        parse_report_artifact="analysis/paper_parse_report.json",
    )
    return document, block, section, chunk


def _evidence(block_id: str) -> EvidenceDraft:
    return EvidenceDraft(
        block_ids=[block_id],
        summary="The experiment uses NTU RGB+D and batch size 32.",
        confidence=0.9,
    )


def _setting_fact(
    fact_id: str,
    *,
    name: str,
    value: str,
    page: int,
) -> PaperFactRecord:
    evidence = PaperEvidence(
        evidence_id=f"e-{fact_id}",
        document_id="paper-test",
        section_id="sec-experiments",
        block_ids=[f"block-{fact_id}"],
        page_start=page,
        page_end=page,
        text=value,
        summary=value,
        content_hash=fact_id.ljust(64, "0")[:64],
        confidence=0.9,
    )
    return PaperFactRecord(
        fact_id=fact_id,
        category="experiment_setting",
        name=name,
        value=value,
        normalized_key=name.casefold(),
        evidence=evidence,
    )


def test_reduce_builds_compatible_summary_and_provenance() -> None:
    document, block, section, chunk = _paper_objects()
    evidence = _evidence(block.block_id)
    extraction = SectionExtractionDraft(
        section_id=section.section_id,
        chunk_id=chunk.chunk_id,
        summary="Experiment setup.",
        research_problem_candidates=[
            TextFactDraft(
                value="Recognize actions in dynamic point clouds.",
                evidence=evidence,
            )
        ],
        datasets=[
            NamedFactDraft(name="NTU RGB+D", evidence=evidence)
        ],
        experiment_settings=[
            ExperimentSettingDraft(
                name="NTU batch size",
                value="32",
                evidence=evidence,
            )
        ],
    )

    summary, facts, conflicts = reduce_section_extractions(
        document=document,
        sections=[section],
        chunks=[chunk],
        blocks=[block],
        extractions=[extraction],
    )

    assert "Recognize actions" in summary.research_problem
    assert summary.datasets == ["NTU RGB+D"]
    assert summary.experiment_settings[0].value == "32"
    legacy = summary.experiment_settings[0].evidence[0]
    assert legacy.section_id == section.section_id
    assert legacy.block_ids == [block.block_id]
    assert legacy.confidence == "high"
    assert facts
    assert conflicts == []


def test_conflicting_settings_are_preserved_and_reported() -> None:
    facts = [
        _setting_fact(
            "f1",
            name="NTU batch size",
            value="32",
            page=14,
        ),
        _setting_fact(
            "f2",
            name="NTU batch size",
            value="16",
            page=18,
        ),
    ]

    conflicts = find_experiment_setting_conflicts(facts)

    assert [fact.value for fact in facts] == ["32", "16"]
    assert len(conflicts) == 1
    assert conflicts[0].values == ["32", "16"]


def test_dataset_scoped_batch_sizes_are_not_a_conflict() -> None:
    facts = [
        _setting_fact(
            "f1",
            name="MSR-Action3D batch size",
            value="16",
            page=14,
        ),
        _setting_fact(
            "f2",
            name="NTU batch size",
            value="32",
            page=14,
        ),
    ]

    assert find_experiment_setting_conflicts(facts) == []