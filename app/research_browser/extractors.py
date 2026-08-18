from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from app.research_browser.errors import ResearchContentRejected
from app.research_browser.identity import sha256_text, stable_id
from app.research_browser.schemas import ExtractedBlock, ResearchSourceKind


SKIPPED_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "form",
    "input",
    "button",
    "select",
    "textarea",
}

BLOCK_TAGS = {
    "title": "title",
    "p": "paragraph",
    "li": "list_item",
    "pre": "code",
    "code": "code",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
}


@dataclass(frozen=True)
class ExtractionResult:
    source_kind: ResearchSourceKind
    title: str | None
    blocks: list[ExtractedBlock]
    normalized_text_sha256: str


class _SemanticHtmlParser(HTMLParser):
    def __init__(self, *, max_blocks: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_blocks = max_blocks
        self.skip_depth = 0
        self.active_tag: str | None = None
        self.active_text: list[str] = []
        self.heading_path: list[str] = []
        self.rows: list[tuple[str, str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        attributes = {str(key).lower(): str(value or "") for key, value in attrs}
        hidden = (
            "hidden" in attributes
            or attributes.get("aria-hidden", "").lower() == "true"
            or "display:none" in attributes.get("style", "").replace(" ", "").lower()
        )
        if self.skip_depth:
            self.skip_depth += 1
            return
        if lowered in SKIPPED_TAGS or hidden:
            self.skip_depth = 1
            return
        if lowered in BLOCK_TAGS:
            self._flush()
            self.active_tag = lowered

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if self.active_tag == tag.lower():
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and self.active_tag is not None:
            self.active_text.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        if self.active_tag is None:
            self.active_text = []
            return
        text = " ".join(" ".join(self.active_text).replace("\x00", " ").split())
        tag = self.active_tag
        self.active_tag = None
        self.active_text = []
        if len(text) < 2 or len(self.rows) >= self.max_blocks:
            return
        text = text[:8000]
        if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            level = int(tag[1])
            self.heading_path = self.heading_path[: level - 1]
            self.heading_path.append(text[:500])
        self.rows.append((BLOCK_TAGS[tag], text, list(self.heading_path)))


def _materialize_blocks(
    rows: list[tuple[str, str, list[str]]],
    *,
    locator_prefix: str,
) -> list[ExtractedBlock]:
    blocks: list[ExtractedBlock] = []
    for index, (kind, text, headings) in enumerate(rows, start=1):
        locator = f"{locator_prefix}:{index}"
        text_hash = sha256_text(text)
        blocks.append(
            ExtractedBlock(
                block_id=stable_id(
                    "rblk",
                    {"locator": locator, "text_sha256": text_hash},
                ),
                kind=kind,
                locator=locator,
                heading_path=headings,
                text=text,
                text_sha256=text_hash,
            )
        )
    return blocks


def extract_html(body: bytes, *, max_blocks: int) -> ExtractionResult:
    # 第一版不依赖服务端 charset 声明，先尝试 UTF-8，再稳定替换非法字节。
    text = body.decode("utf-8", errors="replace")
    parser = _SemanticHtmlParser(max_blocks=max_blocks)
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise ResearchContentRejected("RESEARCH_HTML_PARSE_FAILED") from exc
    blocks = _materialize_blocks(parser.rows, locator_prefix="html:block")
    if not blocks:
        raise ResearchContentRejected("RESEARCH_HTML_HAS_NO_TEXT")
    title = next((block.text for block in blocks if block.kind == "title"), None)
    normalized = "\n".join(block.text for block in blocks)
    return ExtractionResult("html", title, blocks, sha256_text(normalized))


def extract_plain_text(body: bytes, *, max_blocks: int) -> ExtractionResult:
    text = body.decode("utf-8", errors="replace").replace("\x00", " ")
    paragraphs = [" ".join(item.split()) for item in text.split("\n\n")]
    rows = [
        ("paragraph", item[:8000], [])
        for item in paragraphs
        if len(item) >= 2
    ][:max_blocks]
    blocks = _materialize_blocks(rows, locator_prefix="text:block")
    if not blocks:
        raise ResearchContentRejected("RESEARCH_TEXT_HAS_NO_CONTENT")
    normalized = "\n".join(block.text for block in blocks)
    return ExtractionResult("text", None, blocks, sha256_text(normalized))


def extract_pdf(
    body: bytes,
    *,
    max_pages: int,
    max_blocks: int,
) -> ExtractionResult:
    import fitz

    try:
        document = fitz.open(stream=body, filetype="pdf")
    except Exception as exc:
        raise ResearchContentRejected("RESEARCH_PDF_OPEN_FAILED") from exc
    try:
        if document.page_count < 1:
            raise ResearchContentRejected("RESEARCH_PDF_EMPTY")
        rows: list[tuple[str, str, list[str]]] = []
        for page_index in range(min(document.page_count, max_pages)):
            page = document.load_page(page_index)
            text = " ".join(page.get_text("text").replace("\x00", " ").split())
            if text:
                rows.append(("pdf_page", text[:8000], []))
            if len(rows) >= max_blocks:
                break
        blocks = _materialize_blocks(rows, locator_prefix="pdf:page")
        if not blocks:
            raise ResearchContentRejected("RESEARCH_PDF_HAS_NO_TEXT")
        metadata_title = str((document.metadata or {}).get("title") or "").strip()
        normalized = "\n".join(block.text for block in blocks)
        return ExtractionResult(
            "pdf",
            metadata_title[:500] or None,
            blocks,
            sha256_text(normalized),
        )
    finally:
        document.close()


def extract_document(
    *,
    media_type: str,
    body: bytes,
    max_pages: int,
    max_blocks: int,
) -> ExtractionResult:
    if media_type == "text/html":
        return extract_html(body, max_blocks=max_blocks)
    if media_type == "text/plain":
        return extract_plain_text(body, max_blocks=max_blocks)
    if media_type == "application/pdf":
        return extract_pdf(body, max_pages=max_pages, max_blocks=max_blocks)
    raise ResearchContentRejected("RESEARCH_MEDIA_TYPE_DENIED")
