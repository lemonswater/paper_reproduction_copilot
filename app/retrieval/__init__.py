from __future__ import annotations

from app.retrieval.chunking import (
    build_semantic_chunks,
)
from app.retrieval.dense import (
    PreparedDenseRetriever,
    cosine_similarity,
)
from app.retrieval.embedding_backend import (
    EmbeddingBackend,
    EmbeddingProviderError,
    get_embedding_backend,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
)
from app.retrieval.indexer import (
    build_repository_index,
    load_repository_index,
)
from app.retrieval.policy import (
    build_query_features,
    load_retrieval_policy,
    select_retrieval_profile,
    sha256_value,
)
from app.retrieval.policy_schemas import (
    RetrievalDecision,
    RetrievalPolicyConfig,
    RetrievalPolicyMode,
    RetrievalProfile,
    RetrievalQueryFeatures,
)
from app.retrieval.query_builder import (
    build_lexical_query,
    build_semantic_query,
)
from app.retrieval.schemas import (
    CodeEvidence,
    DenseRetrievalReport,
    EvidencePack,
    RepositoryIndex,
    SemanticIndexManifest,
)
from app.retrieval.service import (
    build_evidence_pack,
    validate_code_evidence,
)

__all__ = [
    "CodeEvidence",
    "DenseRetrievalReport",
    "EmbeddingBackend",
    "EmbeddingProviderError",
    "EvidencePack",
    "PreparedDenseRetriever",
    "RepositoryIndex",
    "RetrievalDecision",
    "RetrievalPolicyConfig",
    "RetrievalPolicyMode",
    "RetrievalProfile",
    "RetrievalQueryFeatures",
    "SQLiteEmbeddingCache",
    "SemanticIndexManifest",
    "build_evidence_pack",
    "build_lexical_query",
    "build_query_features",
    "build_repository_index",
    "build_semantic_chunks",
    "build_semantic_query",
    "cosine_similarity",
    "get_embedding_backend",
    "load_repository_index",
    "load_retrieval_policy",
    "select_retrieval_profile",
    "sha256_value",
    "validate_code_evidence",
]