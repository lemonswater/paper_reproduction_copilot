from __future__ import annotations

from app.retrieval.dense import (
    PreparedDenseRetriever,
    cosine_similarity,
)
from app.retrieval.embedding_backend import (
    EmbeddingBackendIdentity,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
)
from app.retrieval.indexer import (
    build_repository_index,
    sha256_text,
)
from app.retrieval.schemas import (
    ChannelHit,
    SemanticChunk,
)
from app.retrieval.service import (
    build_evidence_pack,
)


class FakeEmbeddingBackend:
    def __init__(self) -> None:
        self.document_calls = 0
        self.query_calls = 0

    @property
    def identity(
        self,
    ) -> EmbeddingBackendIdentity:
        return EmbeddingBackendIdentity(
            provider_namespace="fake-provider",
            model="fake-semantic-model",
        )

    @staticmethod
    def _vector(text: str) -> list[float]:
        lower = text.casefold()
        if (
            "radius_neighbors" in lower
            or "motion_offsets" in lower
            or "3d points" in lower
        ):
            return [1.0, 0.05, 0.0]
        if (
            "image" in lower
            or "pixels" in lower
        ):
            return [0.05, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        self.document_calls += 1
        return [
            self._vector(text)
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        self.query_calls += 1
        return self._vector(text)


def _chunk(
    *,
    chunk_id: str,
    file_path: str,
    text: str,
) -> SemanticChunk:
    content_hash = sha256_text(text)
    return SemanticChunk(
        chunk_id=chunk_id,
        repo_fingerprint="repo-fingerprint",
        file_path=file_path,
        file_sha256=(
            f"file-sha-{chunk_id}"
        ),
        start_line=1,
        end_line=10,
        symbol=None,
        source_content_hash=content_hash,
        embedding_content_hash=content_hash,
        embedding_text=text,
    )


def test_dense_retriever_ranks_semantic_operator(
    tmp_path,
):
    backend = FakeEmbeddingBackend()
    retriever = PreparedDenseRetriever.prepare(
        chunks=[
            _chunk(
                chunk_id="operator",
                file_path="operator_core.py",
                text=(
                    "radius_neighbors motion_offsets "
                    "weighted_pool"
                ),
            ),
            _chunk(
                chunk_id="image",
                file_path="image_filter.py",
                text="image pixels average",
            ),
        ],
        backend=backend,
        cache=SQLiteEmbeddingCache(
            tmp_path / "cache.sqlite"
        ),
        cache_version="test-v1",
        batch_size=8,
    )

    hits, report = retriever.rank(
        query=(
            "aggregate neighborhoods of 3D points "
            "across adjacent frames"
        ),
        min_similarity=0.2,
        max_hits=5,
        required=True,
    )

    assert hits[0].file_path == (
        "operator_core.py"
    )
    assert hits[0].channel == "dense"
    assert report.embedding_document_calls == 1
    assert report.embedding_query_calls == 1
    assert report.embedding_dimensions == 3


def test_second_run_uses_document_and_query_cache(
    tmp_path,
):
    cache = SQLiteEmbeddingCache(
        tmp_path / "cache.sqlite"
    )
    chunks = [
        _chunk(
            chunk_id="operator",
            file_path="operator_core.py",
            text="radius_neighbors motion_offsets",
        )
    ]
    first_backend = FakeEmbeddingBackend()
    first = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=first_backend,
        cache=cache,
        cache_version="test-v1",
        batch_size=8,
    )
    first.rank(
        query="3D points across frames",
        min_similarity=0.0,
        max_hits=5,
        required=True,
    )

    second_backend = FakeEmbeddingBackend()
    second = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=second_backend,
        cache=cache,
        cache_version="test-v1",
        batch_size=8,
    )
    _, report = second.rank(
        query="3D points across frames",
        min_similarity=0.0,
        max_hits=5,
        required=True,
    )

    assert second_backend.document_calls == 0
    assert second_backend.query_calls == 0
    assert report.embedding_document_calls == 0
    assert report.embedding_query_calls == 0
    assert report.cache_hits == 2


def test_dense_hit_enters_evidence_pack(
    tmp_path,
):
    path = tmp_path / "operator.py"
    path.write_text(
        "\n".join(
            [
                "class LocalMixer:",
                "    def forward(self, x):",
                "        return aggregate(x)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    _, pack = build_evidence_pack(
        repo_path=tmp_path,
        query="unrelated paper vocabulary",
        keywords=[],
        index=index,
        top_k=3,
        dense_hits=[
            ChannelHit(
                channel="dense",
                file_path="operator.py",
                raw_score=0.92,
                anchor_line=1,
                anchor_end_line=3,
                symbol="LocalMixer",
            )
        ],
    )

    assert pack.items[0].file_path == (
        "operator.py"
    )
    assert "dense" in (
        pack.items[0].retrieval_channels
    )


def test_cosine_similarity_rejects_zero_vector():
    try:
        cosine_similarity(
            [0.0, 0.0],
            [1.0, 0.0],
        )
    except Exception as exc:  # noqa: BLE001
        assert "零向量" in str(exc)
    else:
        raise AssertionError(
            "zero vector should be rejected"
        )