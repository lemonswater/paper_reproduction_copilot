from __future__ import annotations

import math
from dataclasses import dataclass

from app.retrieval.embedding_backend import (
    EmbeddingBackend,
    EmbeddingProviderError,
    validate_vectors,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
    build_embedding_cache_key,
)
from app.retrieval.indexer import sha256_text
from app.retrieval.schemas import (
    ChannelHit,
    DenseRetrievalReport,
    SemanticChunk,
)


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    if not left or len(left) != len(right):
        raise EmbeddingProviderError(
            "Cosine 向量维度不一致"
        )

    dot = sum(
        a * b
        for a, b in zip(left, right)
    )
    left_norm = math.sqrt(
        sum(value * value for value in left)
    )
    right_norm = math.sqrt(
        sum(value * value for value in right)
    )
    if left_norm == 0 or right_norm == 0:
        raise EmbeddingProviderError(
            "Embedding 向量不能是零向量"
        )
    return dot / (left_norm * right_norm)


@dataclass(frozen=True)
class DensePreparationStats:
    cache_hits: int
    cache_misses: int
    embedding_document_calls: int
    dimensions: int


class PreparedDenseRetriever:
    """
    当前 code_search_node 内复用：

    - document chunk 只准备一次；
    - 每个 MethodModule 只新增一个 query embedding；
    - 对象不进入 Graph State 或 checkpoint。
    """

    def __init__(
        self,
        *,
        chunks: list[SemanticChunk],
        vectors_by_chunk_id: dict[
            str,
            list[float],
        ],
        backend: EmbeddingBackend,
        cache: SQLiteEmbeddingCache,
        cache_version: str,
        stats: DensePreparationStats,
    ) -> None:
        self.chunks = chunks
        self.vectors_by_chunk_id = (
            vectors_by_chunk_id
        )
        self.backend = backend
        self.cache = cache
        self.cache_version = cache_version
        self.stats = stats

    @classmethod
    def prepare(
        cls,
        *,
        chunks: list[SemanticChunk],
        backend: EmbeddingBackend,
        cache: SQLiteEmbeddingCache,
        cache_version: str,
        batch_size: int,
    ) -> PreparedDenseRetriever:
        if not chunks:
            raise EmbeddingProviderError(
                "没有可用于 Dense Retrieval 的代码 chunk"
            )
        if batch_size < 1:
            raise ValueError(
                "embedding batch_size 必须大于 0"
            )

        key_by_chunk_id = {
            chunk.chunk_id: (
                build_embedding_cache_key(
                    identity=backend.identity,
                    cache_version=cache_version,
                    value_kind="document",
                    content_hash=(
                        chunk.embedding_content_hash
                    ),
                )
            )
            for chunk in chunks
        }
        cached = cache.get_many(
            list(key_by_chunk_id.values())
        )

        vectors_by_chunk_id: dict[
            str,
            list[float],
        ] = {}
        missing_chunks = []
        for chunk in chunks:
            key = key_by_chunk_id[
                chunk.chunk_id
            ]
            vector = cached.get(key)
            if vector is None:
                missing_chunks.append(chunk)
            else:
                vectors_by_chunk_id[
                    chunk.chunk_id
                ] = vector

        document_calls = 0
        for offset in range(
            0,
            len(missing_chunks),
            batch_size,
        ):
            batch = missing_chunks[
                offset:offset + batch_size
            ]
            vectors = backend.embed_documents(
                [
                    chunk.embedding_text
                    for chunk in batch
                ]
            )
            validate_vectors(
                vectors,
                expected_count=len(batch),
            )
            document_calls += 1

            rows = []
            for chunk, vector in zip(
                batch,
                vectors,
            ):
                vectors_by_chunk_id[
                    chunk.chunk_id
                ] = vector
                rows.append(
                    (
                        key_by_chunk_id[
                            chunk.chunk_id
                        ],
                        chunk.embedding_content_hash,
                        vector,
                    )
                )
            cache.put_many(
                identity=backend.identity,
                cache_version=cache_version,
                value_kind="document",
                values=rows,
            )

        all_vectors = list(
            vectors_by_chunk_id.values()
        )
        dimensions = validate_vectors(
            all_vectors,
            expected_count=len(chunks),
        )

        return cls(
            chunks=chunks,
            vectors_by_chunk_id=(
                vectors_by_chunk_id
            ),
            backend=backend,
            cache=cache,
            cache_version=cache_version,
            stats=DensePreparationStats(
                cache_hits=(
                    len(chunks)
                    - len(missing_chunks)
                ),
                cache_misses=len(
                    missing_chunks
                ),
                embedding_document_calls=(
                    document_calls
                ),
                dimensions=dimensions,
            ),
        )

    def rank(
        self,
        *,
        query: str,
        min_similarity: float,
        max_hits: int,
        required: bool,
    ) -> tuple[
        list[ChannelHit],
        DenseRetrievalReport,
    ]:
        if not query.strip():
            raise ValueError(
                "Dense query 不能为空"
            )
        if not 0 <= min_similarity <= 1:
            raise ValueError(
                "min_similarity 必须位于 [0, 1]"
            )
        if max_hits < 1:
            raise ValueError(
                "dense max_hits 必须大于 0"
            )

        query_hash = sha256_text(query)
        query_key = build_embedding_cache_key(
            identity=self.backend.identity,
            cache_version=self.cache_version,
            value_kind="query",
            content_hash=query_hash,
        )
        cached_query = self.cache.get_many(
            [query_key]
        ).get(query_key)
        query_calls = 0
        if cached_query is None:
            query_vector = (
                self.backend.embed_query(query)
            )
            query_calls = 1
            self.cache.put_many(
                identity=self.backend.identity,
                cache_version=self.cache_version,
                value_kind="query",
                values=[
                    (
                        query_key,
                        query_hash,
                        query_vector,
                    )
                ],
            )
            query_cache_hit = 0
            query_cache_miss = 1
        else:
            query_vector = cached_query
            query_cache_hit = 1
            query_cache_miss = 0

        validate_vectors(
            [query_vector],
            expected_count=1,
            expected_dimensions=(
                self.stats.dimensions
            ),
        )

        chunk_hits = []
        for chunk in self.chunks:
            similarity = cosine_similarity(
                query_vector,
                self.vectors_by_chunk_id[
                    chunk.chunk_id
                ],
            )
            # 负 cosine 没有检索价值；ChannelHit 要求非负。
            score = max(0.0, similarity)
            if score < min_similarity:
                continue
            chunk_hits.append(
                ChannelHit(
                    channel="dense",
                    file_path=chunk.file_path,
                    raw_score=score,
                    anchor_line=chunk.start_line,
                    anchor_end_line=(
                        chunk.end_line
                    ),
                    symbol=chunk.symbol,
                )
            )

        chunk_hits.sort(
            key=lambda item: (
                -item.raw_score,
                item.file_path,
                item.anchor_line,
                item.symbol or "",
            )
        )

        # RRF 的每个通道按文件排名，保留同一文件的最佳 chunk。
        best_by_file: dict[
            str,
            ChannelHit,
        ] = {}
        for hit in chunk_hits:
            best_by_file.setdefault(
                hit.file_path,
                hit,
            )
        hits = list(
            best_by_file.values()
        )[:max_hits]

        return hits, DenseRetrievalReport(
            enabled=True,
            required=required,
            provider_namespace=(
                self.backend
                .identity
                .provider_namespace
            ),
            model=self.backend.identity.model,
            embedding_dimensions=(
                self.stats.dimensions
            ),
            query_hash=query_hash,
            chunk_count=len(self.chunks),
            cache_hits=(
                self.stats.cache_hits
                + query_cache_hit
            ),
            cache_misses=(
                self.stats.cache_misses
                + query_cache_miss
            ),
            embedding_document_calls=(
                self.stats.embedding_document_calls
            ),
            embedding_query_calls=query_calls,
            hits=hits,
        )