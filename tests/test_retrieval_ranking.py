from __future__ import annotations

from app.retrieval import ranking
from app.retrieval.schemas import RepositoryIndex


def _empty_index() -> RepositoryIndex:
    return RepositoryIndex(
        index_version="test-v1",
        repo_root="/repo",
        repo_fingerprint="fingerprint",
    )


def test_rank_keyword_splits_multiline_query_before_search(
    monkeypatch,
) -> None:
    captured_values: list[str] = []

    def fake_search_keywords(
        repo_path: str,
        keywords: list[str],
        max_per_keyword: int,
    ) -> list[dict]:
        assert repo_path == "/repo"
        assert max_per_keyword == 30
        captured_values.extend(keywords)
        return []

    monkeypatch.setattr(
        ranking,
        "search_keywords",
        fake_search_keywords,
    )

    hits = ranking.rank_keyword(
        _empty_index(),
        query=(
            "ad_hoc_retrieval\n"
            "PST convolution spatio temporal point tube"
        ),
        keywords=["PSTConv", "PSTConvTranspose"],
    )

    assert hits == []
    assert captured_values == [
        "PSTConv",
        "PSTConvTranspose",
        "ad_hoc_retrieval",
        "PST convolution spatio temporal point tube",
    ]
    assert all(
        "\n" not in value and "\r" not in value
        for value in captured_values
    )
