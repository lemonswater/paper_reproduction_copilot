from __future__ import annotations

import sqlite3

from app.retrieval.embedding_backend import (
    EmbeddingBackendIdentity,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
    build_embedding_cache_key,
)


def _identity() -> EmbeddingBackendIdentity:
    return EmbeddingBackendIdentity(
        provider_namespace="fake-provider",
        model="fake-model",
    )


def test_embedding_cache_round_trip(
    tmp_path,
):
    cache = SQLiteEmbeddingCache(
        tmp_path / "embeddings.sqlite"
    )
    key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        content_hash="content-hash",
    )

    cache.put_many(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        values=[
            (
                key,
                "content-hash",
                [1.0, 0.5, 0.25],
            )
        ],
    )

    assert cache.get_many([key]) == {
        key: [1.0, 0.5, 0.25]
    }


def test_cache_key_separates_query_and_document():
    document_key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        content_hash="same",
    )
    query_key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="query",
        content_hash="same",
    )

    assert document_key != query_key


def test_corrupt_cache_entry_becomes_miss(
    tmp_path,
):
    path = tmp_path / "embeddings.sqlite"
    cache = SQLiteEmbeddingCache(path)
    key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        content_hash="content-hash",
    )
    cache.put_many(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        values=[
            (
                key,
                "content-hash",
                [1.0, 0.0],
            )
        ],
    )

    with sqlite3.connect(path) as connection:
        connection.execute(
            (
                "UPDATE embedding_cache "
                "SET vector_json = ? "
                "WHERE cache_key = ?"
            ),
            ("not-json", key),
        )

    assert cache.get_many([key]) == {}