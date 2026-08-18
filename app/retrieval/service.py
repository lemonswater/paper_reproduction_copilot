from __future__ import annotations

import hashlib
from pathlib import Path

from app.retrieval.indexer import (
    build_repository_index,
    repository_revision,
    sha256_path,
)
from app.retrieval.ranking import (
    build_channel_rankings,
    fuse_rankings,
)
from app.retrieval.schemas import (
    ChannelHit,
    CodeEvidence,
    EvidencePack,
    FusedCandidate,
    RepositoryIndex,
    RetrievalChannel,
    RetrievalSignal,
)
from app.tools.code_tools import read_file_slice


def _sha256(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def _safe_file(
    root: Path,
    relative_path: str,
) -> Path:
    candidate = (root / relative_path).resolve()
    if (
        candidate == root
        or root not in candidate.parents
        or not candidate.is_file()
    ):
        raise ValueError(
            f"Evidence 文件越界或不存在：{relative_path}"
        )
    return candidate


def _anchor_signal(
    candidate: FusedCandidate,
) -> RetrievalSignal:
    if not candidate.signals:
        raise ValueError(
            "FusedCandidate 缺少 retrieval signal"
        )
    # ranking.py 已按确定性 anchor priority 排序。
    return candidate.signals[0]


def _line_window(
    *,
    candidate: FusedCandidate,
    line_count: int,
    context_lines: int,
    max_span_lines: int,
) -> tuple[int, int, str | None]:
    signal = _anchor_signal(candidate)
    start = max(
        1,
        signal.anchor_line - context_lines,
    )
    anchor_end = (
        signal.anchor_end_line
        or signal.anchor_line
    )
    end = min(
        line_count,
        anchor_end + context_lines,
    )

    if end - start + 1 > max_span_lines:
        end = min(
            line_count,
            start + max_span_lines - 1,
        )

    return start, max(start, end), signal.symbol


def _evidence_id(
    *,
    repo_fingerprint: str,
    file_path: str,
    start_line: int,
    end_line: int,
    content_hash: str,
) -> str:
    payload = "|".join(
        [
            repo_fingerprint,
            file_path,
            str(start_line),
            str(end_line),
            content_hash,
        ]
    )
    return f"code-{_sha256(payload)[:20]}"



def build_evidence_pack(
    *,
    repo_path: str | Path,
    query: str,
    keywords: list[str],
    index: RepositoryIndex | None = None,
    index_version: str = "phase20-v1",
    max_file_bytes: int = 1024 * 1024,
    top_k: int = 8,
    context_lines: int = 20,
    max_span_lines: int = 120,
    rrf_k: int = 60,
    preferred_paths: list[str] | None = None,
    dense_hits: list[ChannelHit] | None = None,
    enabled_channels: list[RetrievalChannel] | None = None,
    channel_weights: dict[RetrievalChannel, float] | None = None,
) -> tuple[RepositoryIndex, EvidencePack]:
    root = Path(repo_path).expanduser().resolve()
    active_index = index or build_repository_index(
        root,
        index_version=index_version,
        max_file_bytes=max_file_bytes,
    )
    if Path(active_index.repo_root).resolve() != root:
        raise ValueError(
            "RepositoryIndex 与 repo_path 不一致"
        )

    normalized_keywords = list(
        dict.fromkeys(
            value.strip()
            for value in keywords
            if value.strip()
        )
    )
    rankings = build_channel_rankings(
        active_index,
        query=query,
        keywords=normalized_keywords,
        preferred_paths=preferred_paths,
        dense_hits=dense_hits,
        enabled_channels=enabled_channels,
    )
    fused = fuse_rankings(
        rankings,
        rrf_k=rrf_k,
        weights=channel_weights,
    )
    documents = {
        document.file_path: document
        for document in active_index.documents
    }
    evidence_items: list[CodeEvidence] = []

    for candidate in fused[: max(top_k, 0)]:
        document = documents.get(candidate.file_path)
        if document is None:
            continue
        path = _safe_file(root, candidate.file_path)

        # 索引后文件发生变化时，不允许继续产生旧 Evidence。
        current_file_sha256 = sha256_path(path)
        if current_file_sha256 != document.file_sha256:
            continue

        start_line, end_line, symbol = _line_window(
            candidate=candidate,
            line_count=document.line_count,
            context_lines=context_lines,
            max_span_lines=max_span_lines,
        )
        text = read_file_slice(
            str(path),
            start_line,
            end_line,
        )
        content_hash = _sha256(text)
        channels = list(
            dict.fromkeys(
                signal.channel
                for signal in candidate.signals
            )
        )

        evidence_items.append(
            CodeEvidence(
                evidence_id=_evidence_id(
                    repo_fingerprint=(
                        active_index.repo_fingerprint
                    ),
                    file_path=candidate.file_path,
                    start_line=start_line,
                    end_line=end_line,
                    content_hash=content_hash,
                ),
                repo_revision=(
                    active_index.repo_revision
                ),
                repo_fingerprint=(
                    active_index.repo_fingerprint
                ),
                file_path=candidate.file_path,
                file_sha256=current_file_sha256,
                start_line=start_line,
                end_line=end_line,
                symbol=symbol,
                retrieval_channels=channels,
                retrieval_signals=(
                    candidate.signals
                ),
                fused_score=candidate.fused_score,
                content_hash=content_hash,
                text=text,
            )
        )

    return active_index, EvidencePack(
        query=query,
        keywords=normalized_keywords,
        repo_revision=active_index.repo_revision,
        repo_fingerprint=(
            active_index.repo_fingerprint
        ),
        items=evidence_items,
    )


def validate_code_evidence(
    *,
    repo_path: str | Path,
    evidence: CodeEvidence,
) -> bool:
    root = Path(repo_path).expanduser().resolve()
    try:
        path = _safe_file(root, evidence.file_path)
    except ValueError:
        return False

    if sha256_path(path) != evidence.file_sha256:
        return False

    current_revision = repository_revision(root)
    if (
        evidence.repo_revision is not None
        and current_revision != evidence.repo_revision
    ):
        return False

    text = read_file_slice(
        str(path),
        evidence.start_line,
        evidence.end_line,
    )
    return _sha256(text) == evidence.content_hash