from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import fitz

from app.paper.indexer import parse_paper_source
from app.paper.pdf_parser import (
    extract_pdf_blocks,
    extract_pdf_tables,
    mark_repeated_marginalia,
)
from app.paper.schemas import PaperBlock
from app.paper.sectioning import build_sections


def _write_fixture_pdf(
    path: Path,
    *,
    blank_second_page: bool = False,
) -> None:
    """动态创建小 PDF，避免 parser 单测依赖真实论文。"""

    document = fitz.open()

    page1 = document.new_page()
    page1.insert_text(
        (72, 40),
        "Repeated Conference Header",
        fontsize=8,
    )
    # 标题放在 y=130，避免进入 parser 的顶部页眉判定区域。
    page1.insert_text((72, 130), "1 Introduction", fontsize=14)
    page1.insert_text(
        (72, 170),
        "Introduction body with enough extracted text.",
        fontsize=10,
    )

    page2 = document.new_page()
    if not blank_second_page:
        page2.insert_text(
            (72, 40),
            "Repeated Conference Header",
            fontsize=8,
        )
        page2.insert_text((72, 130), "2 Experiments", fontsize=14)
        page2.insert_text(
            (72, 170),
            "We train all networks for 35 epochs.",
            fontsize=10,
        )

    document.save(path)
    document.close()


def _block(
    block_id: str,
    *,
    page: int,
    order: int,
    text: str,
    block_type: str,
) -> PaperBlock:
    """构造不依赖 PDF 文件的 sectioning 输入。"""

    return PaperBlock(
        block_id=block_id,
        page=page,
        order=order,
        block_type=block_type,
        text=text,
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def test_pdf_parser_preserves_pages_and_marks_header(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fixture.pdf"
    _write_fixture_pdf(path)

    blocks, warnings, page_count = extract_pdf_blocks(path)
    marked = mark_repeated_marginalia(
        blocks,
        page_count=page_count,
    )

    assert page_count == 2
    assert {block.page for block in marked} == {1, 2}
    assert any(
        block.text == "1 Introduction"
        for block in marked
    )
    assert any(
        block.block_type == "header"
        and block.excluded
        and block.exclusion_reason == "repeated_page_header"
        for block in marked
    )
    assert warnings == []


def test_same_pdf_produces_stable_block_ids(tmp_path: Path) -> None:
    path = tmp_path / "stable.pdf"
    _write_fixture_pdf(path)

    first, _, _ = extract_pdf_blocks(path)
    second, _, _ = extract_pdf_blocks(path)

    assert [
        (block.block_id, block.page, block.order, block.text)
        for block in first
    ] == [
        (block.block_id, block.page, block.order, block.text)
        for block in second
    ]


def test_blank_page_records_warnings_and_is_not_indexed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "blank-page.pdf"
    _write_fixture_pdf(path, blank_second_page=True)

    _, warnings, page_count = extract_pdf_blocks(path)
    warning_keys = {
        (warning.code, warning.page)
        for warning in warnings
    }

    assert page_count == 2
    assert ("EMPTY_PAGE", 2) in warning_keys
    assert ("OCR_REQUIRED", 2) in warning_keys

    parsed = parse_paper_source(path)
    assert parsed.report.page_count == 2
    assert parsed.report.indexed_pages == [1]
    assert parsed.report.empty_pages == [2]
    assert parsed.report.ocr_required_pages == [2]
    assert parsed.report.status == "partial"


def test_arxiv_overlay_does_not_become_section() -> None:
    overlay = _block(
        "overlay",
        page=1,
        order=0,
        text="arXiv:2205.13713v1 [cs.CV] 27 May 2022",
        block_type="heading",
    )
    heading = _block(
        "intro-heading",
        page=1,
        order=1,
        text="1 Introduction",
        block_type="heading",
    )
    body = _block(
        "intro-body",
        page=1,
        order=2,
        text="This paper studies dynamic point clouds.",
        block_type="paragraph",
    )

    sections = build_sections([overlay, heading, body])

    assert [section.title for section in sections] == [
        "Introduction"
    ]
    assert all(
        "arxiv" not in section.normalized_title
        for section in sections
    )


def test_table_extraction_failure_becomes_warning(
    tmp_path: Path,
) -> None:
    """find_tables() 异常只能产生 warning，不能让 parser 崩溃。"""

    class FailingPage:
        def find_tables(self):
            raise RuntimeError("synthetic table failure")

    class FakeDocument:
        page_count = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def load_page(self, index: int):
            assert index == 0
            return FailingPage()

    with patch(
        "app.paper.pdf_parser.fitz.open",
        return_value=FakeDocument(),
    ):
        blocks, warnings = extract_pdf_tables(
            tmp_path / "not-opened.pdf"
        )

    assert blocks == []
    assert len(warnings) == 1
    assert warnings[0].code == "TABLE_PARSE_FAILED"
    assert warnings[0].page == 1
    assert "synthetic table failure" in warnings[0].message