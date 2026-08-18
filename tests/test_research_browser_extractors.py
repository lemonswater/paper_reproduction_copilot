import pytest

from app.research_browser.errors import ResearchContentRejected
from app.research_browser.extractors import (
    extract_document,
    extract_html,
    extract_plain_text,
)
from app.research_browser.identity import sha256_text


def test_html_drops_script_style_form() -> None:
    body = b"""
    <html>
    <head><title>Test</title></head>
    <body>
    <h1>Heading</h1>
    <p>Content paragraph.</p>
    <li>List item.</li>
    <script>alert('evil')</script>
    <style>.x{color:red}</style>
    <form action="https://example.org/write"></form>
    </body>
    </html>
    """
    result = extract_html(body, max_blocks=20)
    texts = [block.text for block in result.blocks]
    assert not any("alert" in t for t in texts)
    assert not any("color:red" in t for t in texts)
    assert any("Content paragraph" in t for t in texts)
    assert any("List item" in t for t in texts)
    assert result.title == "Test"


def test_html_preserves_heading_path() -> None:
    body = b"""
    <html><body>
    <h1>Main</h1>
    <p>Under main.</p>
    <h2>Sub</h2>
    <p>Under sub.</p>
    </body></html>
    """
    result = extract_html(body, max_blocks=20)
    para_blocks = [b for b in result.blocks if b.kind == "paragraph"]
    assert len(para_blocks) >= 2
    assert "Main" in para_blocks[0].heading_path
    assert "Sub" in para_blocks[1].heading_path


def test_html_block_count_limited() -> None:
    body = b"<html><body>"
    for i in range(50):
        body += f"<p>Paragraph {i}</p>".encode()
    body += b"</body></html>"
    result = extract_html(body, max_blocks=5)
    assert len(result.blocks) <= 5


def test_plain_text_splits_paragraphs() -> None:
    body = b"First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = extract_plain_text(body, max_blocks=20)
    assert len(result.blocks) == 3
    assert result.blocks[0].text == "First paragraph."
    assert result.blocks[1].text == "Second paragraph."


def test_plain_text_removes_nul() -> None:
    body = b"Hello\x00World"
    result = extract_plain_text(body, max_blocks=20)
    assert "\x00" not in result.blocks[0].text


def test_html_rejects_empty() -> None:
    with pytest.raises(ResearchContentRejected):
        extract_html(b"<html><body></body></html>", max_blocks=20)


def test_plain_text_rejects_empty() -> None:
    with pytest.raises(ResearchContentRejected):
        extract_plain_text(b"\n\n\n", max_blocks=20)


def test_unknown_media_type_rejected() -> None:
    with pytest.raises(ResearchContentRejected):
        extract_document(
            media_type="image/png",
            body=b"png",
            max_pages=5,
            max_blocks=20,
        )


def test_same_input_produces_same_ids() -> None:
    body = b"<html><body><p>Same content.</p></body></html>"
    r1 = extract_html(body, max_blocks=20)
    r2 = extract_html(body, max_blocks=20)
    assert r1.blocks[0].block_id == r2.blocks[0].block_id
    assert r1.normalized_text_sha256 == r2.normalized_text_sha256
    assert r1.normalized_text_sha256 == sha256_text(
        "\n".join(b.text for b in r1.blocks)
    )


def test_html_block_text_capped() -> None:
    long_text = "A" * 10000
    body = f"<html><body><p>{long_text}</p></body></html>".encode()
    result = extract_html(body, max_blocks=20)
    assert len(result.blocks[0].text) <= 8000


def test_pdf_extraction(tmp_path) -> None:
    pytest.importorskip("fitz")
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "PSTNet PDF page content.")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_document(
        media_type="application/pdf",
        body=pdf_bytes,
        max_pages=5,
        max_blocks=20,
    )
    assert result.source_kind == "pdf"
    assert len(result.blocks) >= 1
    assert "PSTNet" in result.blocks[0].text


def test_pdf_rejects_empty_body() -> None:
    pytest.importorskip("fitz")
    import fitz

    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    with pytest.raises(ResearchContentRejected):
        extract_document(
            media_type="application/pdf",
            body=pdf_bytes,
            max_pages=5,
            max_blocks=20,
        )
