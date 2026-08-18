from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.config import settings
from app.paper.pdf_parser import (
    extract_pdf_blocks,
    extract_pdf_tables,
    mark_repeated_marginalia,
    parse_text_blocks,
)
from app.paper.schemas import (
    PaperBlock,
    PaperDocument,
    PaperParseReport,
    PaperParseWarning,
    PaperSection,
)
from app.paper.sectioning import (
    SectionBuildResult,
    build_sections_with_diagnostics,
)
from app.schemas import ArtifactRecord
from app.tools.artifact_tools import (
    sha256_file,
    write_json_artifact,
)
from app.tools.paper_tools import read_text_file


@dataclass(frozen=True)
class ParsedPaper:
    """不依赖 Graph state 的确定性解析结果。"""

    source_path: Path
    source_sha256: str
    page_count: int
    blocks: list[PaperBlock]
    sections: list[PaperSection]
    report: PaperParseReport


@dataclass(frozen=True)
class PaperIndexResult:
    """解析结果及其 run-native Artifact。"""

    parsed: ParsedPaper
    document: PaperDocument
    document_path: Path
    blocks_path: Path
    sections_path: Path
    report_path: Path
    records: list[ArtifactRecord]


def _parse_status(
    *,
    indexed_pages: list[int],
    warnings: list[PaperParseWarning],
) -> Literal["succeeded", "partial", "failed"]:
    """根据正文覆盖率和解析告警计算文本提取状态。"""

    # 只有页眉、页脚等 excluded block 时，仍然没有可用正文。
    if not indexed_pages:
        return "failed"
    if warnings:
        return "partial"
    return "succeeded"


def _structure_status(
    result: SectionBuildResult,
) -> Literal["reliable", "degraded", "unknown"]:
    """结构状态与文本提取状态分开计算。"""

    if (
        not result.sections
        or (
            len(result.sections) == 1
            and result.sections[0].title == "Document"
        )
    ):
        return "unknown"

    if result.hierarchy_warning_count:
        return "degraded"

    return "reliable"


def parse_paper_source(paper_path: str | Path) -> ParsedPaper:
    """解析 PDF/Markdown/TXT，但不写 Artifact。"""

    source_path = Path(paper_path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"未找到论文文件：{source_path}")

    suffix = source_path.suffix.casefold()
    warnings: list[PaperParseWarning]

    if suffix == ".pdf":
        blocks, warnings, page_count = extract_pdf_blocks(
            source_path,
            min_extracted_chars=settings.paper_min_extracted_chars,
        )
        blocks = mark_repeated_marginalia(
            blocks,
            page_count=page_count,
        )
        table_blocks, table_warnings = extract_pdf_tables(source_path)
        blocks.extend(table_blocks)
        warnings.extend(table_warnings)
    elif suffix in {".md", ".txt"}:
        blocks = parse_text_blocks(read_text_file(str(source_path)))
        warnings = []
        page_count = 1
    else:
        raise ValueError(f"不支持的论文格式：{suffix}")

    blocks.sort(key=lambda item: (item.page, item.order))
    section_result = build_sections_with_diagnostics(blocks)
    sections = section_result.sections
    warnings.extend(section_result.warnings)

    # build_sections() 在找不到 heading 时会创建 Document fallback。
    # fallback 可继续使用，但必须在 report 中显式可见。
    if (
        sections
        and len(sections) == 1
        and sections[0].title == "Document"
    ):
        warnings.append(
            PaperParseWarning(
                code="NO_HEADINGS",
                message=(
                    "No reliable headings were detected; "
                    "the document fallback section is used."
                ),
            )
        )

    indexed_pages = sorted(
        {
            block.page
            for block in blocks
            if not block.excluded and block.text.strip()
        }
    )
    report = PaperParseReport(
        status=_parse_status(
            indexed_pages=indexed_pages,
            warnings=warnings,
        ),
        structure_status=_structure_status(
            section_result
        ),
        page_count=page_count,
        indexed_pages=indexed_pages,
        empty_pages=sorted(
            {
                warning.page
                for warning in warnings
                if warning.code == "EMPTY_PAGE"
                and warning.page is not None
            }
        ),
        ocr_required_pages=sorted(
            {
                warning.page
                for warning in warnings
                if warning.code == "OCR_REQUIRED"
                and warning.page is not None
            }
        ),
        block_count=len(blocks),
        section_count=len(sections),
        heading_candidate_count=(
            section_result.heading_candidate_count
        ),
        accepted_heading_count=(
            section_result.accepted_heading_count
        ),
        rejected_heading_count=(
            section_result.rejected_heading_count
        ),
        multiline_heading_merge_count=(
            section_result.multiline_heading_merge_count
        ),
        hierarchy_warning_count=(
            section_result.hierarchy_warning_count
        ),
        warnings=warnings,
    )
    return ParsedPaper(
        source_path=source_path,
        source_sha256=sha256_file(source_path),
        page_count=page_count,
        blocks=blocks,
        sections=sections,
        report=report,
    )


def persist_paper_index(
    *,
    state: dict,
    parsed: ParsedPaper,
) -> PaperIndexResult:
    """把解析结果写入当前 run，并返回全部 ArtifactRecord。"""

    blocks_relative = "analysis/paper_blocks.json"
    sections_relative = "analysis/paper_sections.json"
    report_relative = "analysis/paper_parse_report.json"

    blocks_path, blocks_record = write_json_artifact(
        state=state,
        relative_path=blocks_relative,
        payload=[
            block.model_dump(mode="json")
            for block in parsed.blocks
        ],
        producer_node="paper_reader",
    )
    sections_path, sections_record = write_json_artifact(
        state=state,
        relative_path=sections_relative,
        payload=[
            section.model_dump(mode="json")
            for section in parsed.sections
        ],
        producer_node="paper_reader",
    )
    report_path, report_record = write_json_artifact(
        state=state,
        relative_path=report_relative,
        payload=parsed.report.model_dump(mode="json"),
        producer_node="paper_reader",
    )

    document = PaperDocument(
        document_id=f"paper-{parsed.source_sha256[:16]}",
        source_path=str(parsed.source_path),
        source_sha256=parsed.source_sha256,
        parser_version=settings.paper_parser_version,
        page_count=parsed.page_count,
        indexed_page_count=len(parsed.report.indexed_pages),
        block_count=len(parsed.blocks),
        section_count=len(parsed.sections),
        blocks_artifact=blocks_relative,
        sections_artifact=sections_relative,
        parse_report_artifact=report_relative,
    )
    document_path, document_record = write_json_artifact(
        state=state,
        relative_path="analysis/paper_document.json",
        payload=document.model_dump(mode="json"),
        producer_node="paper_reader",
    )

    return PaperIndexResult(
        parsed=parsed,
        document=document,
        document_path=document_path,
        blocks_path=blocks_path,
        sections_path=sections_path,
        report_path=report_path,
        records=[
            document_record,
            blocks_record,
            sections_record,
            report_record,
        ],
    )


def index_paper_to_artifacts(
    *,
    state: dict,
    paper_path: str | Path,
) -> PaperIndexResult:
    """Graph 节点和 CLI 共用的 run-native 索引入口。"""

    return persist_paper_index(
        state=state,
        parsed=parse_paper_source(paper_path),
    )


def load_paper_blocks(path: str | Path) -> list[PaperBlock]:
    """从已受控的 Artifact 路径加载并重新校验 block。"""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("paper_blocks Artifact 必须是 JSON list")
    return [PaperBlock.model_validate(item) for item in payload]


def load_paper_sections(path: str | Path) -> list[PaperSection]:
    """从已受控的 Artifact 路径加载并重新校验 section。"""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("paper_sections Artifact 必须是 JSON list")
    return [PaperSection.model_validate(item) for item in payload]
