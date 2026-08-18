from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from app.nodes.paper_reader_node import paper_reader_node


@pytest.fixture
def fixture_pdf(tmp_path: Path) -> Path:
    """创建两页最小 PDF，避免 reader 测试依赖真实论文。"""

    path = tmp_path / "fixture.pdf"
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
    return path


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """创建完全没有原生文本的 PDF。"""

    path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    return path


def _relative_paths(result: dict) -> set[str]:
    return {
        item["relative_path"]
        for item in result.get("artifact_records", [])
    }


def test_paper_reader_writes_index_without_embedding_blocks(
    run_state: dict,
    fixture_pdf: Path,
) -> None:
    state = {
        **run_state,
        "paper_path": str(fixture_pdf),
    }

    result = paper_reader_node(state)

    document = result["paper_document"]
    assert document["page_count"] == 2
    assert document["indexed_page_count"] == 2
    assert document["block_count"] > 0
    assert document["section_count"] >= 2

    assert Path(result["paper_blocks_path"]).is_file()
    assert Path(result["paper_sections_path"]).is_file()
    assert Path(result["paper_parse_report_path"]).is_file()

    assert "paper_blocks" not in result
    assert "paper_sections" not in result
    assert "paper_text_chunks" not in result
    assert "paper_text" not in result

    assert {
        "analysis/paper_document.json",
        "analysis/paper_blocks.json",
        "analysis/paper_sections.json",
        "analysis/paper_parse_report.json",
    } <= _relative_paths(result)

    report = json.loads(
        Path(result["paper_parse_report_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "succeeded"
    assert report["indexed_pages"] == [1, 2]


def test_paper_reader_missing_path_is_terminal(
    run_state: dict,
) -> None:
    result = paper_reader_node(dict(run_state))

    assert result["paper_document"] == {}
    assert result["paper_blocks_path"] is None
    assert result["paper_sections_path"] is None
    assert result["paper_parse_report_path"] is None
    assert result["final_status"] == "invalid_input"
    assert result["active_stage_error"]["code"] == (
        "PAPER_PATH_MISSING"
    )
    assert result["active_stage_error"]["terminal"] is True
    assert {
        "reports/error_report.json",
        "reports/error_report.md",
    } <= _relative_paths(result)


def test_paper_reader_blank_pdf_persists_failed_index(
    run_state: dict,
    blank_pdf: Path,
) -> None:
    state = {
        **run_state,
        "paper_path": str(blank_pdf),
    }

    result = paper_reader_node(state)

    assert result["paper_document"]["page_count"] == 1
    assert result["paper_document"]["indexed_page_count"] == 0
    assert result["final_status"] == "invalid_input"
    assert result["active_stage_error"]["code"] == (
        "PAPER_PARSE_FAILED"
    )
    assert result["active_stage_error"]["terminal"] is True

    report = json.loads(
        Path(result["paper_parse_report_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "failed"
    assert report["empty_pages"] == [1]
    assert report["ocr_required_pages"] == [1]

    assert {
        "analysis/paper_document.json",
        "analysis/paper_blocks.json",
        "analysis/paper_sections.json",
        "analysis/paper_parse_report.json",
        "reports/error_report.json",
        "reports/error_report.md",
    } <= _relative_paths(result)