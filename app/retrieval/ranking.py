from __future__ import annotations

import math
import re
from collections import defaultdict

from app.retrieval.indexer import tokenize
from app.retrieval.schemas import (
    ChannelHit,
    FusedCandidate,
    RepositoryIndex,
    RetrievalChannel,
    RetrievalSignal,
)
from app.tools.search_tools import search_keywords

DEFAULT_CHANNEL_WEIGHTS: dict[
    RetrievalChannel,
    float,
] = {
    "traceback": 3.0,
    "symbol": 2.4,
    "dense": 2.1,
    "keyword": 2.0,
    "import_graph": 1.7,
    "cli_config": 1.6,
    "path": 1.2,
    "bm25": 1.0,
}

_ANCHOR_PRIORITY: dict[
    RetrievalChannel,
    int,
] = {
    "traceback": 8,
    "symbol": 7,
    "dense": 6,
    "keyword": 5,
    "cli_config": 4,
    "import_graph": 3,
    "path": 2,
    "bm25": 1,
}


def _identifier_key(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        value.casefold(),
    )


def _query_values(
    query: str,
    keywords: list[str],
) -> list[str]:
    values: list[str] = []
    for raw_value in [*keywords, query]:
        # rg 的逐行 literal 搜索不接受包含真实换行符的 pattern。
        # query 仍由其他检索通道按整体语义使用，这里只拆分搜索值。
        for line in raw_value.splitlines():
            normalized = " ".join(line.split())
            if (
                normalized
                and len(normalized) <= 160
                and normalized not in values
            ):
                values.append(normalized)
    return values


def _best_per_file(
    hits: list[ChannelHit],
) -> list[ChannelHit]:
    best: dict[str, ChannelHit] = {}
    for hit in hits:
        previous = best.get(hit.file_path)
        if previous is None or (
            hit.raw_score,
            -hit.anchor_line,
        ) > (
            previous.raw_score,
            -previous.anchor_line,
        ):
            best[hit.file_path] = hit

    return sorted(
        best.values(),
        key=lambda item: (
            -item.raw_score,
            item.file_path,
            item.anchor_line,
        ),
    )


def rank_keyword(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
) -> list[ChannelHit]:
    values = _query_values(query, keywords)
    if not values:
        return []

    known_paths = {
        document.file_path
        for document in index.documents
    }
    matches = search_keywords(
        index.repo_root,
        values,
        max_per_keyword=30,
    )
    hits = []

    for match in matches:
        file_path = str(match["file_path"])
        if file_path not in known_paths:
            continue
        keyword = str(match.get("keyword") or "")
        # 更长的 literal 通常比单字符命中更有区分度。
        score = 1.0 + min(len(keyword), 80) / 80.0
        hits.append(
            ChannelHit(
                channel="keyword",
                file_path=file_path,
                raw_score=score,
                anchor_line=int(match["line"]),
            )
        )

    return _best_per_file(hits)


def rank_symbol(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
) -> list[ChannelHit]:
    values = _query_values(query, keywords)
    value_keys = {
        _identifier_key(value)
        for value in values
        if _identifier_key(value)
    }
    query_tokens = set(
        tokenize(" ".join(values))
    )
    hits: list[ChannelHit] = []

    for symbol in index.symbols:
        symbol_key = _identifier_key(symbol.name)
        qualified_key = _identifier_key(
            symbol.qualified_name
        )
        symbol_tokens = set(
            tokenize(symbol.qualified_name)
        )

        exact = any(
            key in {symbol_key, qualified_key}
            for key in value_keys
        )
        contains = any(
            key in symbol_key
            or symbol_key in key
            for key in value_keys
        )
        overlap = len(query_tokens & symbol_tokens)

        if exact:
            score = 4.0
        elif contains and symbol_key:
            score = 2.5
        elif overlap:
            score = 1.0 + overlap
        else:
            continue

        hits.append(
            ChannelHit(
                channel="symbol",
                file_path=symbol.file_path,
                raw_score=score,
                anchor_line=symbol.start_line,
                anchor_end_line=symbol.end_line,
                symbol=symbol.qualified_name,
            )
        )

    return _best_per_file(hits)


def _module_name_from_path(file_path: str) -> str:
    value = file_path.removesuffix(".py")
    return value.replace("/", ".")


def rank_import_graph(
    index: RepositoryIndex,
    *,
    symbol_hits: list[ChannelHit],
    query: str,
    keywords: list[str],
) -> list[ChannelHit]:
    target_modules = {
        _module_name_from_path(hit.file_path)
        for hit in symbol_hits
    }
    target_names = {
        _identifier_key(hit.symbol or "")
        for hit in symbol_hits
        if hit.symbol
    }
    target_names.update(
        _identifier_key(value)
        for value in _query_values(query, keywords)
    )
    target_names.discard("")

    hits: list[ChannelHit] = []

    for record in index.imports:
        module_match = any(
            (
                record.imported_module == module
                or module.endswith(
                    f".{record.imported_module}"
                )
                or record.imported_module.endswith(
                    f".{module}"
                )
            )
            for module in target_modules
            if record.imported_module
        )
        imported_name_keys = {
            _identifier_key(name)
            for name in record.imported_names
        }
        name_match = bool(
            imported_name_keys & target_names
        )

        if not module_match and not name_match:
            continue

        hits.append(
            ChannelHit(
                channel="import_graph",
                file_path=record.file_path,
                raw_score=(
                    2.0
                    if module_match and name_match
                    else 1.0
                ),
                anchor_line=record.line,
            )
        )

    return _best_per_file(hits)


def rank_path(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
) -> list[ChannelHit]:
    query_tokens = set(
        tokenize(
            " ".join(
                _query_values(query, keywords)
            )
        )
    )
    hits: list[ChannelHit] = []

    for document in index.documents:
        path_tokens = set(
            tokenize(document.file_path)
        )
        overlap = query_tokens & path_tokens
        if not overlap:
            continue
        hits.append(
            ChannelHit(
                channel="path",
                file_path=document.file_path,
                raw_score=float(len(overlap)),
                anchor_line=1,
            )
        )

    return _best_per_file(hits)


def rank_cli_config(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
) -> list[ChannelHit]:
    query_tokens = set(
        tokenize(
            " ".join(
                _query_values(query, keywords)
            )
        )
    )
    hits: list[ChannelHit] = []

    for option in index.cli_options:
        option_text = " ".join(
            [
                *option.flags,
                option.dest or "",
                option.default_repr or "",
                option.help_text or "",
            ]
        )
        option_tokens = set(tokenize(option_text))
        overlap = query_tokens & option_tokens
        if not overlap:
            continue
        hits.append(
            ChannelHit(
                channel="cli_config",
                file_path=option.file_path,
                raw_score=(
                    1.0 + float(len(overlap))
                ),
                anchor_line=option.line,
            )
        )

    return _best_per_file(hits)


def rank_bm25(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
    k1: float = 1.5,
    b: float = 0.75,
) -> list[ChannelHit]:
    query_terms = list(
        dict.fromkeys(
            tokenize(
                " ".join(
                    _query_values(query, keywords)
                )
            )
        )
    )
    documents = index.documents
    if not query_terms or not documents:
        return []

    document_count = len(documents)
    average_length = (
        sum(
            document.token_count
            for document in documents
        )
        / document_count
    ) or 1.0

    document_frequency = {
        term: sum(
            term in document.term_frequencies
            for document in documents
        )
        for term in query_terms
    }
    hits: list[ChannelHit] = []

    for document in documents:
        score = 0.0
        length = max(document.token_count, 1)

        for term in query_terms:
            frequency = document.term_frequencies.get(
                term,
                0,
            )
            if frequency == 0:
                continue

            df = document_frequency[term]
            inverse_document_frequency = math.log(
                1.0
                + (
                    document_count - df + 0.5
                )
                / (df + 0.5)
            )
            denominator = frequency + k1 * (
                1.0
                - b
                + b * length / average_length
            )
            score += (
                inverse_document_frequency
                * frequency
                * (k1 + 1.0)
                / denominator
            )

        if score <= 0:
            continue
        hits.append(
            ChannelHit(
                channel="bm25",
                file_path=document.file_path,
                raw_score=score,
                anchor_line=1,
            )
        )

    return _best_per_file(hits)


def rank_traceback_paths(
    index: RepositoryIndex,
    *,
    preferred_paths: list[str],
) -> list[ChannelHit]:
    documents = {
        document.file_path
        for document in index.documents
    }
    hits: list[ChannelHit] = []

    for position, file_path in enumerate(
        preferred_paths
    ):
        if file_path not in documents:
            continue
        hits.append(
            ChannelHit(
                channel="traceback",
                file_path=file_path,
                raw_score=max(
                    1.0,
                    10.0 - position,
                ),
                anchor_line=1,
            )
        )

    return _best_per_file(hits)


def build_channel_rankings(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
    preferred_paths: list[str] | None = None,
    dense_hits: list[ChannelHit] | None = None,
    enabled_channels: list[RetrievalChannel] | None = None,
) -> dict[
    RetrievalChannel,
    list[ChannelHit],
]:
    """
    只构造 profile 允许的通道。

    enabled_channels=None 保持 Phase 20/21 的全部通道行为，供 off/shadow
    模式和旧调用方使用。函数只控制候选生成，不改变 repo/path 边界。
    """

    all_channels: list[RetrievalChannel] = [
        "traceback",
        "symbol",
        "dense",
        "keyword",
        "import_graph",
        "cli_config",
        "path",
        "bm25",
    ]
    active = set(enabled_channels or all_channels)

    unknown = active - set(all_channels)
    if unknown:
        raise ValueError(
            f"未知 retrieval channel：{sorted(unknown)}"
        )
    if "import_graph" in active and "symbol" not in active:
        raise ValueError(
            "import_graph 依赖 symbol，不能单独启用"
        )

    # import graph 依赖 symbol seed，因此只在确实需要时计算。
    symbol_hits = (
        rank_symbol(
            index,
            query=query,
            keywords=keywords,
        )
        if "symbol" in active
        else []
    )

    rankings: dict[
        RetrievalChannel,
        list[ChannelHit],
    ] = {}

    if "traceback" in active:
        rankings["traceback"] = rank_traceback_paths(
            index,
            preferred_paths=preferred_paths or [],
        )
    if "symbol" in active:
        rankings["symbol"] = symbol_hits
    if "dense" in active:
        rankings["dense"] = list(dense_hits or [])
    if "keyword" in active:
        rankings["keyword"] = rank_keyword(
            index,
            query=query,
            keywords=keywords,
        )
    if "import_graph" in active:
        rankings["import_graph"] = rank_import_graph(
            index,
            symbol_hits=symbol_hits,
            query=query,
            keywords=keywords,
        )
    if "cli_config" in active:
        rankings["cli_config"] = rank_cli_config(
            index,
            query=query,
            keywords=keywords,
        )
    if "path" in active:
        rankings["path"] = rank_path(
            index,
            query=query,
            keywords=keywords,
        )
    if "bm25" in active:
        rankings["bm25"] = rank_bm25(
            index,
            query=query,
            keywords=keywords,
        )

    return rankings

def fuse_rankings(
    rankings: dict[
        RetrievalChannel,
        list[ChannelHit],
    ],
    *,
    rrf_k: int = 60,
    weights: dict[
        RetrievalChannel,
        float,
    ] | None = None,
) -> list[FusedCandidate]:
    if rrf_k < 1:
        raise ValueError("rrf_k 必须大于 0")

    active_weights = {
        **DEFAULT_CHANNEL_WEIGHTS,
        **(weights or {}),
    }
    scores: dict[str, float] = defaultdict(float)
    signals: dict[
        str,
        list[RetrievalSignal],
    ] = defaultdict(list)

    for channel, hits in rankings.items():
        for rank, hit in enumerate(hits, start=1):
            scores[hit.file_path] += (
                active_weights[channel]
                / (rrf_k + rank)
            )
            signals[hit.file_path].append(
                RetrievalSignal(
                    channel=channel,
                    rank=rank,
                    raw_score=hit.raw_score,
                    anchor_line=hit.anchor_line,
                    anchor_end_line=(
                        hit.anchor_end_line
                    ),
                    symbol=hit.symbol,
                )
            )

    candidates = [
        FusedCandidate(
            file_path=file_path,
            fused_score=score,
            signals=sorted(
                signals[file_path],
                key=lambda item: (
                    -_ANCHOR_PRIORITY[
                        item.channel
                    ],
                    item.rank,
                ),
            ),
        )
        for file_path, score in scores.items()
    ]
    return sorted(
        candidates,
        key=lambda item: (
            -item.fused_score,
            item.file_path,
        ),
    )
