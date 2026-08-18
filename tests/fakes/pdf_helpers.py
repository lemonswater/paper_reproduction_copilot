"""Phase 29 test helpers for PDF resource validation.

fitz (PyMuPDF) may or may not be installed in the test environment.
When it IS installed, ``validate_pdf`` performs full parsing and rejects
dummy content. These helpers generate a real minimal valid PDF when fitz
is available, and fall back to magic-bytes-only content otherwise.
"""

from __future__ import annotations

from pathlib import Path


def make_valid_pdf_bytes() -> bytes:
    """Return bytes of a minimal valid PDF.

    Uses fitz to generate a real 1-page PDF when available so that
    ``validate_pdf`` can fully parse it. Falls back to a magic-bytes-only
    blob when fitz is absent (validator then skips parser check).
    """

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return b"%PDF-1.4\n%dummy"

    document = fitz.open()
    document.new_page()
    data = document.tobytes()
    document.close()
    return data


def write_valid_pdf(path: Path) -> None:
    """Write a minimal valid PDF to ``path``."""

    path.write_bytes(make_valid_pdf_bytes())
