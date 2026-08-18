from __future__ import annotations

import hashlib
from pathlib import Path
from statistics import median
from typing import Any

import fitz

from app.paper.normalization import (
    looks_like_arxiv_overlay,
    normalize_key,
    normalize_pdf_text,
)
from app.paper.schemas import PaperBlock, PaperParseWarning


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_block_id(page: int, order: int, text: str) -> str:
    """相同 PDF 和 parser 规则应始终得到相同 block_id。"""

    short_hash = sha256_text(text)[:10]
    return f"p{page:03d}-b{order:04d}-{short_hash}"


def _span_style(line: dict[str, Any]) -> tuple[float | None, str | None, bool]:
    """从 line 的 spans 中提取主要字号、字体和粗体信息。"""

    spans = line.get("spans", [])
    if not spans:
        return None, None, False

    # 选择字符数最多的 span 作为该 line 的主要样式。
    dominant = max(
        spans,
        key=lambda span: len(str(span.get("text", ""))),
    )
    font_name = str(dominant.get("font", "")) or None
    font_size = float(dominant.get("size", 0.0)) or None
    is_bold = bool(font_name and "bold" in font_name.casefold())
    return font_size, font_name, is_bold


def _line_text(line: dict[str, Any]) -> str:
    """合并同一视觉行中的所有 span。"""

    return normalize_pdf_text(
        "".join(str(span.get("text", "")) for span in line.get("spans", []))
    )


def _looks_like_caption(text: str) -> bool:
    value = text.casefold()
    return value.startswith(("figure ", "fig. ", "table "))


def _provisional_type(
    *,
    text: str,
    font_size: float | None,
    body_font_size: float,
    is_bold: bool,
) -> str:
    """只做视觉层初判，真正 heading 判断在 sectioning 阶段完成。"""

    if _looks_like_caption(text):
        return "caption"
    if looks_like_arxiv_overlay(text):
        return "unknown"
    if font_size and font_size >= body_font_size * 1.45:
        return "title"
    if is_bold or (font_size and font_size >= body_font_size * 1.15):
        return "heading"
    return "paragraph"


def _estimate_body_font(raw_pages: list[dict[str, Any]]) -> float:
    """使用正文候选 span 的字号中位数，避免标题字号拉高平均值。"""

    sizes: list[float] = []
    for page in raw_pages:
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = normalize_pdf_text(str(span.get("text", "")))
                    size = float(span.get("size", 0.0))
                    if len(text) >= 20 and 5.0 <= size <= 20.0:
                        sizes.extend([size] * min(len(text), 200))
    return float(median(sizes)) if sizes else 10.0


def extract_pdf_blocks(
    path: str | Path,
    *,
    min_extracted_chars: int = 20,
) -> tuple[list[PaperBlock], list[PaperParseWarning], int]:
    """将 PDF 提取为按页排序的 PaperBlock。"""

    source = Path(path).expanduser().resolve()
    warnings: list[PaperParseWarning] = []
    blocks: list[PaperBlock] = []

    with fitz.open(source) as document:
        page_count = document.page_count
        raw_pages = [
            document.load_page(index).get_text("dict", sort=True)
            for index in range(page_count)
        ]
        body_font_size = _estimate_body_font(raw_pages)

        for page_index, raw_page in enumerate(raw_pages):
            page_number = page_index + 1
            page_char_count = 0
            order = 0

            for raw_block in raw_page.get("blocks", []):
                # PyMuPDF type=0 是文本；图像等对象留给后续多模态阶段。
                if raw_block.get("type", 0) != 0:
                    continue

                for line in raw_block.get("lines", []):
                    text = _line_text(line)
                    if not text:
                        continue

                    font_size, font_name, is_bold = _span_style(line)
                    block_type = _provisional_type(
                        text=text,
                        font_size=font_size,
                        body_font_size=body_font_size,
                        is_bold=is_bold,
                    )
                    bbox_value = line.get("bbox")
                    bbox = (
                        tuple(float(value) for value in bbox_value)
                        if bbox_value and len(bbox_value) == 4
                        else None
                    )

                    block = PaperBlock(
                        block_id=_stable_block_id(page_number, order, text),
                        page=page_number,
                        order=order,
                        block_type=block_type,
                        text=text,
                        bbox=bbox,
                        font_size=font_size,
                        font_name=font_name,
                        is_bold=is_bold,
                        text_hash=sha256_text(text),
                    )
                    blocks.append(block)
                    page_char_count += len(text)
                    order += 1

            if page_char_count == 0:
                warnings.append(
                    PaperParseWarning(
                        code="EMPTY_PAGE",
                        page=page_number,
                        message="No text blocks were extracted from this page.",
                    )
                )
                warnings.append(
                    PaperParseWarning(
                        code="OCR_REQUIRED",
                        page=page_number,
                        message="The page may be image-only and requires OCR.",
                    )
                )
            elif page_char_count < min_extracted_chars:
                warnings.append(
                    PaperParseWarning(
                        code="OCR_REQUIRED",
                        page=page_number,
                        message=(
                            "Very little text was extracted; verify whether "
                            "the page requires OCR."
                        ),
                    )
                )

    return blocks, warnings, page_count

def mark_repeated_marginalia(
    blocks: list[PaperBlock],
    *,
    page_count: int,
    repetition_ratio: float = 0.35,
) -> list[PaperBlock]:
    """标记在多页顶部/底部重复出现的页眉页脚。"""

    if page_count <= 1:
        return blocks

    pages_by_text: dict[str, set[int]] = {}
    candidates: dict[str, list[PaperBlock]] = {}

    for block in blocks:
        if block.bbox is None:
            continue

        # PDF 坐标原点通常位于页面左上角。
        top = block.bbox[1]
        bottom = block.bbox[3]

        # 第一版使用较保守的绝对坐标；后续可改为页面高度比例。
        if top > 90.0 and bottom < 700.0:
            continue

        key = normalize_key(block.text)
        if not key:
            continue
        pages_by_text.setdefault(key, set()).add(block.page)
        candidates.setdefault(key, []).append(block)

    repeated_keys = {
        key
        for key, pages in pages_by_text.items()
        if len(pages) / page_count >= repetition_ratio
    }

    updated: list[PaperBlock] = []
    for block in blocks:
        key = normalize_key(block.text)
        if key not in repeated_keys:
            updated.append(block)
            continue

        if block.bbox and block.bbox[1] <= 90.0:
            block_type = "header"
            reason = "repeated_page_header"
        else:
            block_type = "footer"
            reason = "repeated_page_footer"

        updated.append(
            block.model_copy(
                update={
                    "block_type": block_type,
                    "excluded": True,
                    "exclusion_reason": reason,
                }
            )
        )

    return updated

def extract_pdf_tables(
    path: str | Path,
) -> tuple[list[PaperBlock], list[PaperParseWarning]]:
    """尝试提取表格；失败时只记录 warning，不猜测单元格。"""

    source = Path(path).expanduser().resolve()
    table_blocks: list[PaperBlock] = []
    warnings: list[PaperParseWarning] = []

    with fitz.open(source) as document:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            page_number = page_index + 1

            if not hasattr(page, "find_tables"):
                # 当前 PyMuPDF 不支持时，不把每页都记成失败。
                continue

            try:
                finder = page.find_tables()
                tables = list(getattr(finder, "tables", []))
            except Exception as exc:
                warnings.append(
                    PaperParseWarning(
                        code="TABLE_PARSE_FAILED",
                        page=page_number,
                        message=f"Table extraction failed: {type(exc).__name__}: {exc}",
                    )
                )
                continue

            for table_index, table in enumerate(tables):
                try:
                    rows = table.extract()
                    normalized_rows = [
                        [
                            normalize_pdf_text(str(cell or ""))
                            for cell in row
                        ]
                        for row in rows
                    ]
                    text = "\n".join(
                        " | ".join(row) for row in normalized_rows
                    ).strip()
                    if not text:
                        raise ValueError("table extractor returned no cells")

                    order = 100_000 + table_index
                    table_blocks.append(
                        PaperBlock(
                            block_id=_stable_block_id(
                                page_number,
                                order,
                                text,
                            ),
                            page=page_number,
                            order=order,
                            block_type="table",
                            text=text,
                            bbox=tuple(float(value) for value in table.bbox),
                            text_hash=sha256_text(text),
                        )
                    )
                except Exception as exc:
                    warnings.append(
                        PaperParseWarning(
                            code="TABLE_PARSE_FAILED",
                            page=page_number,
                            message=(
                                "A table was detected but its cells could not "
                                f"be recovered: {type(exc).__name__}: {exc}"
                            ),
                        )
                    )

    return table_blocks, warnings

def parse_text_blocks(text: str) -> list[PaperBlock]:
    blocks: list[PaperBlock] = []

    for order, raw_line in enumerate(text.splitlines()):
        line = normalize_pdf_text(raw_line)
        if not line:
            continue

        markdown_heading = line.startswith("#")
        clean_text = line.lstrip("#").strip() if markdown_heading else line
        text_hash = sha256_text(clean_text)

        blocks.append(
            PaperBlock(
                block_id=_stable_block_id(1, order, clean_text),
                page=1,
                order=order,
                block_type="heading" if markdown_heading else "paragraph",
                text=clean_text,
                text_hash=text_hash,
            )
        )

    return blocks