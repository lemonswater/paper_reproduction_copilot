from __future__ import annotations

import re
from pathlib import Path

from app.retrieval.indexer import (
    sha256_path,
    sha256_text,
)
from app.retrieval.schemas import (
    RepositoryIndex,
    SemanticChunk,
    SemanticChunkMetadata,
    SemanticIndexManifest,
)
from app.tools.repo_tools import (
    MAPPING_RELEVANT_SUFFIXES,
)

# Dense Retrieval 与确定性 RepositoryIndex 使用同一文件边界，只让 Python
# 源码、配置、实验脚本和说明文档参与论文语义匹配。
SEMANTIC_SUFFIXES = MAPPING_RELEVANT_SUFFIXES

_SECRET_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    (
        \b(?:
            api[_-]?key
            |access[_-]?token
            |auth[_-]?token
            |password
            |passwd
            |client[_-]?secret
            |private[_-]?key
        )\b
        \s*[:=]\s*
    )
    .+$
    """
)

_PRIVATE_KEY_MARKER_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    re.IGNORECASE,
)


def _safe_file(
    root: Path,
    relative_path: str,
) -> Path:
    unresolved = root / relative_path
    if unresolved.is_symlink():
        raise ValueError(
            "Semantic chunk 不允许读取软链接："
            f"{relative_path}"
        )
    candidate = unresolved.resolve()
    if (
        candidate == root
        or root not in candidate.parents
        or not candidate.is_file()
    ):
        raise ValueError(
            "Semantic chunk 文件越界、缺失或为软链接："
            f"{relative_path}"
        )
    return candidate


def _redact_line(
    line: str,
) -> tuple[str, bool]:
    if _PRIVATE_KEY_MARKER_RE.search(line):
        return "<REDACTED_PRIVATE_KEY>", True

    replaced, count = _SECRET_ASSIGNMENT_RE.subn(
        lambda match: (
            f"{match.group(1)}<REDACTED>"
        ),
        line,
    )
    return replaced, bool(count)


def _windows(
    *,
    start_line: int,
    end_line: int,
    max_lines: int,
    overlap_lines: int,
) -> list[tuple[int, int]]:
    if start_line > end_line:
        return []
    if max_lines < 8:
        raise ValueError(
            "semantic chunk max_lines 不能小于 8"
        )
    if (
        overlap_lines < 0
        or overlap_lines >= max_lines
    ):
        raise ValueError(
            "overlap_lines 必须满足 "
            "0 <= overlap_lines < max_lines"
        )

    step = max_lines - overlap_lines
    output = []
    cursor = start_line
    while cursor <= end_line:
        window_end = min(
            end_line,
            cursor + max_lines - 1,
        )
        output.append((cursor, window_end))
        if window_end >= end_line:
            break
        cursor += step
    return output


def _chunk_id(
    *,
    repo_fingerprint: str,
    file_path: str,
    start_line: int,
    end_line: int,
    symbol: str | None,
    source_content_hash: str,
) -> str:
    payload = "|".join(
        [
            repo_fingerprint,
            file_path,
            str(start_line),
            str(end_line),
            symbol or "<module>",
            source_content_hash,
        ]
    )
    return (
        "semantic-"
        f"{sha256_text(payload)[:24]}"
    )


def _embedding_text(
    *,
    file_path: str,
    symbol: str | None,
    lines: list[str],
) -> str:
    header = [
        f"file: {file_path}",
        f"symbol: {symbol or '<module>'}",
        "code:",
    ]
    return "\n".join(
        [
            *header,
            *lines,
        ]
    )


def build_semantic_chunks(
    *,
    repo_path: str | Path,
    index: RepositoryIndex,
    chunk_policy_version: str,
    max_lines: int = 80,
    overlap_lines: int = 16,
    max_chunks: int = 5000,
) -> tuple[
    list[SemanticChunk],
    SemanticIndexManifest,
]:
    root = Path(repo_path).expanduser().resolve()
    if Path(index.repo_root).resolve() != root:
        raise ValueError(
            "RepositoryIndex 与 semantic repo_path 不一致"
        )
    if max_chunks < 1:
        raise ValueError(
            "semantic max_chunks 必须大于 0"
        )

    symbols_by_file: dict[str, list] = {}
    for symbol in index.symbols:
        symbols_by_file.setdefault(
            symbol.file_path,
            [],
        ).append(symbol)

    chunks: list[SemanticChunk] = []
    warnings: list[str] = []
    total_redacted_lines = 0
    reached_limit = False

    for document in index.documents:
        if reached_limit:
            break
        if (
            Path(document.file_path)
            .suffix.casefold()
            not in SEMANTIC_SUFFIXES
        ):
            continue

        path = _safe_file(
            root,
            document.file_path,
        )
        if sha256_path(path) != document.file_sha256:
            warnings.append(
                "STALE_SOURCE_SKIPPED:"
                f"{document.file_path}"
            )
            continue

        source_lines = path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()
        if not source_lines:
            continue
        if any(
            _PRIVATE_KEY_MARKER_RE.search(line)
            for line in source_lines
        ):
            # 私钥正文跨多行，逐行替换无法可靠保证不泄漏，整文件跳过。
            warnings.append(
                "PRIVATE_KEY_FILE_SKIPPED:"
                f"{document.file_path}"
            )
            continue

        redacted_lines = []
        file_redacted_count = 0
        for line in source_lines:
            redacted, changed = _redact_line(line)
            redacted_lines.append(redacted)
            file_redacted_count += int(changed)
        total_redacted_lines += file_redacted_count

        # 全文件滑动窗口负责 module-level 数据流、import 和不规则代码。
        spans: list[
            tuple[int, int, str | None]
        ] = [
            (
                start,
                end,
                None,
            )
            for start, end in _windows(
                start_line=1,
                end_line=len(source_lines),
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            )
        ]

        # Symbol span 让类和函数边界成为额外的高质量语义 chunk。
        for symbol in symbols_by_file.get(
            document.file_path,
            [],
        ):
            symbol_end = min(
                symbol.end_line,
                len(source_lines),
            )
            for start, end in _windows(
                start_line=symbol.start_line,
                end_line=symbol_end,
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            ):
                spans.append(
                    (
                        start,
                        end,
                        symbol.qualified_name,
                    )
                )

        seen_spans: set[
            tuple[int, int, str | None]
        ] = set()
        for start, end, symbol_name in spans:
            identity = (
                start,
                end,
                symbol_name,
            )
            if identity in seen_spans:
                continue
            seen_spans.add(identity)

            raw_slice = "\n".join(
                source_lines[
                    start - 1:end
                ]
            )
            safe_slice_lines = redacted_lines[
                start - 1:end
            ]
            safe_text = _embedding_text(
                file_path=document.file_path,
                symbol=symbol_name,
                lines=safe_slice_lines,
            )
            source_hash = sha256_text(
                raw_slice
            )

            chunks.append(
                SemanticChunk(
                    chunk_id=_chunk_id(
                        repo_fingerprint=(
                            index.repo_fingerprint
                        ),
                        file_path=(
                            document.file_path
                        ),
                        start_line=start,
                        end_line=end,
                        symbol=symbol_name,
                        source_content_hash=(
                            source_hash
                        ),
                    ),
                    repo_fingerprint=(
                        index.repo_fingerprint
                    ),
                    file_path=(
                        document.file_path
                    ),
                    file_sha256=(
                        document.file_sha256
                    ),
                    start_line=start,
                    end_line=end,
                    symbol=symbol_name,
                    source_content_hash=(
                        source_hash
                    ),
                    embedding_content_hash=(
                        sha256_text(safe_text)
                    ),
                    embedding_text=safe_text,
                    redacted_line_count=sum(
                        1
                        for raw, safe in zip(
                            source_lines[
                                start - 1:end
                            ],
                            safe_slice_lines,
                        )
                        if raw != safe
                    ),
                )
            )

            if len(chunks) >= max_chunks:
                reached_limit = True
                warnings.append(
                    "SEMANTIC_CHUNK_LIMIT_REACHED:"
                    f"{max_chunks}"
                )
                break

    metadata = [
        SemanticChunkMetadata(
            chunk_id=chunk.chunk_id,
            file_path=chunk.file_path,
            file_sha256=chunk.file_sha256,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            symbol=chunk.symbol,
            source_content_hash=(
                chunk.source_content_hash
            ),
            embedding_content_hash=(
                chunk.embedding_content_hash
            ),
            redacted_line_count=(
                chunk.redacted_line_count
            ),
        )
        for chunk in chunks
    ]

    return chunks, SemanticIndexManifest(
        index_version=index.index_version,
        chunk_policy_version=(
            chunk_policy_version
        ),
        repo_root=str(root),
        repo_revision=index.repo_revision,
        repo_fingerprint=(
            index.repo_fingerprint
        ),
        chunk_count=len(chunks),
        redacted_line_count=(
            total_redacted_lines
        ),
        chunks=metadata,
        warnings=warnings,
    )
