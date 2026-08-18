from __future__ import annotations

import pytest

from app.retrieval.query_builder import (
    build_lexical_query,
    build_semantic_query,
)


def test_semantic_query_includes_paper_evidence():
    module = {
        "name": "Point tube aggregation",
        "description": (
            "Aggregate local geometry across frames"
        ),
        "possible_keywords": [
            "point tube",
            "temporal radius",
        ],
        "evidence": [
            {
                "quote_or_summary": (
                    "Neighbors are grouped in space "
                    "and time before feature pooling."
                )
            }
        ],
    }

    lexical = build_lexical_query(module)
    semantic = build_semantic_query(module)

    assert "Point tube aggregation" in lexical
    assert "Neighbors are grouped" not in lexical
    assert "module behavior:" in semantic
    assert "paper terminology:" in semantic
    assert "Neighbors are grouped" in semantic


def test_semantic_query_is_bounded():
    module = {
        "name": "module",
        "description": "behavior",
        "evidence": [
            {
                "quote_or_summary": "x" * 1000
            }
            for _ in range(20)
        ],
    }

    query = build_semantic_query(
        module,
        max_chars=300,
    )

    assert len(query) <= 300


def test_semantic_query_rejects_empty_module():
    with pytest.raises(
        ValueError,
        match="无法构造",
    ):
        build_semantic_query({})