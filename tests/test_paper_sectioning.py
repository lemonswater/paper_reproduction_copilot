from __future__ import annotations

import hashlib

from app.paper.schemas import PaperBlock
from app.paper.sectioning import (
    build_sections,
    build_sections_with_diagnostics,
)


def _block(
    block_id: str,
    page: int,
    order: int,
    text: str,
    block_type: str = "paragraph",
    bbox: tuple[float, float, float, float] | None = None,
    *,
    font_size: float | None = None,
    font_name: str | None = None,
    is_bold: bool = False,
) -> PaperBlock:
    return PaperBlock(
        block_id=block_id,
        page=page,
        order=order,
        block_type=block_type,
        text=text,
        bbox=bbox,
        font_size=font_size,
        font_name=font_name,
        is_bold=is_bold,
        text_hash=hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest(),
    )


def test_build_sections_recognizes_body_and_appendix() -> None:
    blocks = [
        _block("b1", 1, 0, "Abstract", "heading"),
        _block("b2", 1, 1, "We study point cloud sequences."),
        _block("b3", 6, 0, "4 Experiments", "heading"),
        _block("b4", 6, 1, "We evaluate on three datasets."),
        _block("b5", 14, 0, "C Implementation Details", "heading"),
        _block("b6", 14, 1, "We train all networks for 35 epochs."),
    ]

    sections = build_sections(blocks)

    assert [section.kind for section in sections] == [
        "abstract",
        "experiments",
        "implementation",
    ]
    assert sections[-1].number == "C"
    assert sections[-1].page_start == 14
    assert "b6" in sections[-1].block_ids


def test_build_sections_merges_split_number_and_title_blocks() -> None:
    blocks = [
        _block(
            "experiments-number",
            6,
            90,
            "4",
            "heading",
            (108.3, 666.2, 114.3, 678.1),
        ),
        _block(
            "experiments-title",
            6,
            91,
            "EXPERIMENTS",
            bbox=(126.8, 666.2, 200.1, 678.1),
        ),
        _block("experiments-body", 6, 92, "Experiment body."),
        _block(
            "ablation-number",
            9,
            56,
            "4.3",
            bbox=(108.2, 310.6, 121.7, 320.5),
        ),
        _block(
            "ablation-title",
            9,
            57,
            "ABLATION STUDY",
            bbox=(132.2, 310.6, 209.1, 320.5),
        ),
        _block("ablation-body", 9, 58, "Ablation body."),
        _block(
            "implementation-number",
            14,
            129,
            "C",
            "heading",
            (108.3, 368.2, 116.3, 380.2),
        ),
        _block(
            "implementation-title",
            14,
            130,
            "IMPLEMENTATION DETAILS",
            bbox=(128.8, 368.2, 268.7, 380.2),
        ),
        _block("implementation-body", 14, 131, "Training details."),
    ]

    sections = build_sections(blocks)

    assert [
        (section.number, section.title, section.kind)
        for section in sections
    ] == [
        ("4", "EXPERIMENTS", "experiments"),
        ("4.3", "ABLATION STUDY", "ablation"),
        ("C", "IMPLEMENTATION DETAILS", "implementation"),
    ]
    assert sections[1].parent_id == sections[0].section_id
    assert "experiments-title" in sections[0].block_ids
    assert "implementation-title" in sections[2].block_ids


def test_split_heading_does_not_merge_formula_fragment() -> None:
    blocks = [
        _block(
            "symbol",
            4,
            10,
            "W",
            "heading",
            (108.0, 200.0, 116.0, 212.0),
        ),
        _block(
            "formula",
            4,
            11,
            "(x, y, z)",
            bbox=(126.0, 200.0, 170.0, 212.0),
        ),
        _block("body", 4, 12, "Formula explanation."),
    ]

    sections = build_sections(blocks)

    assert len(sections) == 1
    assert sections[0].title == "Document"
    assert sections[0].number is None


def test_repeated_header_is_not_a_section() -> None:
    blocks = [
        _block(
            "header",
            1,
            0,
            "Published as a conference paper at ICLR 2021",
            "header",
        ).model_copy(
            update={
                "excluded": True,
                "exclusion_reason": "repeated_page_header",
            }
        ),
        _block("abstract", 1, 1, "Abstract", "heading"),
        _block("body", 1, 2, "Paper body."),
    ]

    sections = build_sections(blocks)

    assert len(sections) == 1
    assert sections[0].title == "Abstract"


def test_arxiv_overlay_is_not_a_section() -> None:
    blocks = [
        _block(
            "overlay",
            1,
            0,
            "arXiv:2205.13713v1 [cs.CV] 27 May 2022",
            "title",
        ),
        _block("abstract", 1, 1, "Abstract", "heading"),
        _block("body", 1, 2, "Paper body."),
    ]

    sections = build_sections(blocks)

    assert [section.title for section in sections] == ["Abstract"]

def test_numbered_paragraph_and_table_values_are_rejected() -> None:
    blocks = [
        _block(
            "year",
            2,
            0,
            (
                "2018) and pooling techniques "
                "(Fan et al., 2017) are employed."
            ),
        ),
        _block(
            "table-row",
            2,
            1,
            "89.39 97.68 69.43 86.52",
            "table",
        ),
        _block(
            "experiments",
            6,
            0,
            "4 EXPERIMENTS",
            "heading",
        ),
        _block(
            "body",
            6,
            1,
            "We evaluate the model.",
        ),
    ]

    sections = build_sections(blocks)

    assert [
        (section.number, section.title)
        for section in sections
    ] == [("4", "EXPERIMENTS")]


def test_formula_and_single_symbol_are_not_sections() -> None:
    blocks = [
        _block(
            "formula-f",
            4,
            0,
            "F ′(x,y,z)",
            "heading",
        ),
        _block(
            "formula-m",
            4,
            1,
            "M (x,y,z)",
            "heading",
        ),
        _block(
            "symbol-w",
            4,
            2,
            "W",
            "heading",
        ),
        _block(
            "real-heading",
            4,
            3,
            "3.2.2 POINT TUBE",
            "heading",
        ),
        _block(
            "body",
            4,
            4,
            "Point tube description.",
        ),
    ]

    sections = build_sections(blocks)

    assert [
        (section.number, section.title)
        for section in sections
    ] == [("3.2.2", "POINT TUBE")]


def test_vertical_figure_label_is_not_a_section() -> None:
    blocks = [
        _block(
            "vertical-label",
            21,
            0,
            "PSTConv1: N=1024",
            "heading",
            (100.0, 100.0, 109.0, 181.0),
        ),
        _block(
            "limitation",
            21,
            1,
            "O LIMITATION",
            "heading",
            (120.0, 200.0, 220.0, 214.0),
        ),
        _block(
            "body",
            21,
            2,
            "Limitation body.",
        ),
    ]

    sections = build_sections(blocks)

    assert [
        (section.number, section.title)
        for section in sections
    ] == [("O", "LIMITATION")]


def test_multiline_main_title_is_merged() -> None:
    blocks = [
        _block(
            "title-line-1",
            1,
            0,
            "PSTNET: POINT SPATIO-TEMPORAL CONVOLUTION",
            "heading",
            (108.4, 80.5, 503.6, 97.7),
            font_size=13.77,
            font_name="NimbusRomNo9L-Regu",
        ),
        _block(
            "title-line-2",
            1,
            1,
            "ON POINT CLOUD SEQUENCES",
            "heading",
            (108.4, 100.4, 331.8, 117.6),
            font_size=13.77,
            font_name="NimbusRomNo9L-Regu",
        ),
        _block(
            "abstract",
            1,
            2,
            "ABSTRACT",
            "heading",
            (108.0, 150.0, 180.0, 164.0),
            font_size=11.0,
            font_name="NimbusRomNo9L-Regu",
        ),
        _block(
            "body",
            1,
            3,
            "Abstract body.",
        ),
    ]

    result = build_sections_with_diagnostics(blocks)

    assert result.sections[0].title == (
        "PSTNET: POINT SPATIO-TEMPORAL CONVOLUTION "
        "ON POINT CLOUD SEQUENCES"
    )
    assert result.multiline_heading_merge_count == 1
    assert result.sections[1].title == "ABSTRACT"


def test_multiline_split_appendix_title_is_merged() -> None:
    blocks = [
        _block(
            "appendix-number",
            19,
            28,
            "M",
            "heading",
            (108.3, 568.6, 118.9, 580.6),
            font_size=11.96,
            font_name="NimbusRomNo9L-Regu",
        ),
        _block(
            "appendix-title",
            19,
            29,
            (
                "VISUALIZATION OF THE OUTPUT OF EACH "
                "PST CONVOLUTION LAYER IN"
            ),
            "paragraph",
            (131.5, 568.6, 503.7, 580.6),
            font_size=9.54,
            font_name="NimbusRomNo9L-Regu",
        ),
        _block(
            "appendix-title-continuation",
            19,
            30,
            "PSTNET",
            "heading",
            (131.5, 582.6, 175.4, 594.5),
            font_size=11.96,
            font_name="NimbusRomNo9L-Regu",
        ),
        _block(
            "body",
            19,
            31,
            "We visualize each layer.",
        ),
    ]

    result = build_sections_with_diagnostics(blocks)

    assert len(result.sections) == 1
    assert result.sections[0].number == "M"
    assert result.sections[0].title == (
        "VISUALIZATION OF THE OUTPUT OF EACH "
        "PST CONVOLUTION LAYER IN PSTNET"
    )
    assert result.multiline_heading_merge_count == 1


def test_numbered_parent_is_not_taken_from_recent_stack() -> None:
    blocks = [
        _block(
            "section-3",
            3,
            0,
            "3 METHOD",
            "heading",
        ),
        _block(
            "section-3-2",
            3,
            1,
            "3.2 PST CONVOLUTION",
            "heading",
        ),
        _block(
            "intermediate",
            3,
            2,
            "INTERMEDIATE NOTE",
            "heading",
        ),
        _block(
            "section-3-2-2",
            3,
            3,
            "3.2.2 POINT TUBE",
            "heading",
        ),
        _block(
            "body",
            3,
            4,
            "Point tube body.",
        ),
    ]

    sections = build_sections(blocks)
    by_number = {
        section.number: section
        for section in sections
        if section.number
    }

    assert by_number["3.2.2"].parent_id == (
        by_number["3.2"].section_id
    )


def test_missing_numbered_parent_is_reported() -> None:
    blocks = [
        _block(
            "orphan",
            6,
            0,
            "4.1 ACTION RECOGNITION",
            "heading",
        ),
        _block(
            "body",
            6,
            1,
            "Experiment body.",
        ),
    ]

    result = build_sections_with_diagnostics(blocks)

    assert result.sections[0].parent_id is None
    assert result.hierarchy_warning_count == 1
    assert result.warnings[0].code == (
        "MISSING_SECTION_PARENT"
    )
    assert result.warnings[0].block_id == "orphan"
