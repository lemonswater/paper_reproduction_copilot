from __future__ import annotations

from app.paper.normalization import (
    looks_like_arxiv_overlay,
    normalize_heading,
    normalize_key,
)


def test_normalize_spaced_uppercase_heading() -> None:
    raw = "P ROPOSED P OINT S PATIO -T EMPORAL C ONVOLUTIONAL N ETWORK"

    normalized = normalize_heading(raw)

    assert normalized == (
        "PROPOSED POINT SPATIO-TEMPORAL CONVOLUTIONAL NETWORK"
    )


def test_normalize_key_ignores_formatting_differences() -> None:
    assert normalize_key("Batch Size") == normalize_key("batch-size")


def test_arxiv_overlay_is_not_paper_title() -> None:
    assert looks_like_arxiv_overlay(
        "arXiv:2205.13713v1 [cs.CV] 27 May 2022"
    )