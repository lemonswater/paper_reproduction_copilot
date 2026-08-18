from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RetrievalChannel = Literal[
    "keyword",
    "symbol",
    "import_graph",
    "path",
    "cli_config",
    "bm25",
    "traceback",
    "dense",
]


class RetrievalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IndexedDocument(RetrievalModel):
    file_path: str
    file_sha256: str
    size_bytes: int = Field(ge=0)
    line_count: int = Field(ge=0)
    token_count: int = Field(ge=0)
    term_frequencies: dict[str, int] = Field(
        default_factory=dict
    )


class SymbolRecord(RetrievalModel):
    file_path: str
    name: str
    qualified_name: str
    kind: Literal[
        "class",
        "function",
        "async_function",
        "method",
        "async_method",
    ]
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class ImportRecord(RetrievalModel):
    file_path: str
    imported_module: str
    imported_names: list[str] = Field(default_factory=list)
    line: int = Field(ge=1)


class CliOptionRecord(RetrievalModel):
    file_path: str
    flags: list[str] = Field(default_factory=list)
    dest: str | None = None
    default_repr: str | None = None
    help_text: str | None = None
    line: int = Field(ge=1)


class RepositoryIndex(RetrievalModel):
    index_version: str
    repo_root: str
    repo_revision: str | None = None
    repo_fingerprint: str
    documents: list[IndexedDocument] = Field(
        default_factory=list
    )
    symbols: list[SymbolRecord] = Field(
        default_factory=list
    )
    imports: list[ImportRecord] = Field(
        default_factory=list
    )
    cli_options: list[CliOptionRecord] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)


class SemanticChunk(RetrievalModel):
    """
    仅在 code_search_node 当前进程内使用。

    embedding_text 是脱敏后的 Provider 输入，不写入 checkpoint。
    """

    chunk_id: str
    repo_fingerprint: str
    file_path: str
    file_sha256: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol: str | None = None
    source_content_hash: str
    embedding_content_hash: str
    embedding_text: str
    redacted_line_count: int = Field(default=0, ge=0)


class SemanticChunkMetadata(RetrievalModel):
    """写入 Artifact 的 chunk metadata，不包含源码正文和向量。"""

    chunk_id: str
    file_path: str
    file_sha256: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol: str | None = None
    source_content_hash: str
    embedding_content_hash: str
    redacted_line_count: int = Field(default=0, ge=0)


class SemanticIndexManifest(RetrievalModel):
    index_version: str
    chunk_policy_version: str
    repo_root: str
    repo_revision: str | None = None
    repo_fingerprint: str
    chunk_count: int = Field(ge=0)
    redacted_line_count: int = Field(default=0, ge=0)
    chunks: list[SemanticChunkMetadata] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)


class ChannelHit(RetrievalModel):
    channel: RetrievalChannel
    file_path: str
    raw_score: float = Field(ge=0.0)
    anchor_line: int = Field(default=1, ge=1)
    anchor_end_line: int | None = Field(
        default=None,
        ge=1,
    )
    symbol: str | None = None


class DenseRetrievalReport(RetrievalModel):
    enabled: bool
    required: bool = False
    provider_namespace: str | None = None
    model: str | None = None
    embedding_dimensions: int | None = Field(
        default=None,
        ge=1,
    )
    query_hash: str | None = None
    chunk_count: int = Field(default=0, ge=0)
    cache_hits: int = Field(default=0, ge=0)
    cache_misses: int = Field(default=0, ge=0)
    embedding_document_calls: int = Field(
        default=0,
        ge=0,
    )
    embedding_query_calls: int = Field(
        default=0,
        ge=0,
    )
    hits: list[ChannelHit] = Field(
        default_factory=list
    )
    fallback_reason: str | None = None


class RetrievalSignal(RetrievalModel):
    channel: RetrievalChannel
    rank: int = Field(ge=1)
    raw_score: float = Field(ge=0.0)
    anchor_line: int = Field(ge=1)
    anchor_end_line: int | None = Field(
        default=None,
        ge=1,
    )
    symbol: str | None = None


class FusedCandidate(RetrievalModel):
    file_path: str
    fused_score: float = Field(ge=0.0)
    signals: list[RetrievalSignal] = Field(
        default_factory=list
    )


class CodeEvidence(RetrievalModel):
    evidence_id: str
    repo_revision: str | None = None
    repo_fingerprint: str
    file_path: str
    file_sha256: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol: str | None = None
    retrieval_channels: list[RetrievalChannel] = Field(
        default_factory=list
    )
    retrieval_signals: list[RetrievalSignal] = Field(
        default_factory=list
    )
    fused_score: float = Field(ge=0.0)
    content_hash: str
    text: str


class EvidencePack(RetrievalModel):
    query: str
    keywords: list[str] = Field(default_factory=list)
    repo_revision: str | None = None
    repo_fingerprint: str
    items: list[CodeEvidence] = Field(default_factory=list)