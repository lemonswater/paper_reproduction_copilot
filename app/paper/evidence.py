from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator

from app.paper.schemas import (
    EvidenceDraft,
    PaperBlock,
    PaperDocument,
    PaperEvidence,
    PaperSection,
    SectionChunk,
    SectionExtractionDraft,
)
from app.schemas import Confidence, Evidence


class InvalidEvidenceReference(ValueError):
    """LLM 引用了当前 chunk 之外或不存在的 block。"""


_BLOCK_LOCATOR_RE = re.compile(
    r"^(p\d+-b\d+)(?:-[0-9a-f]+)?$",
    re.IGNORECASE,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _block_locator(block_id: str) -> str | None:
    """提取不含内容哈希的稳定页码/顺序定位符。"""

    match = _BLOCK_LOCATOR_RE.fullmatch(block_id.strip())
    return match.group(1).casefold() if match is not None else None


def _canonical_block_ids(
    requested_ids: list[str],
    *,
    chunk: SectionChunk,
    blocks_by_id: dict[str, PaperBlock],
) -> list[str]:
    """只在当前 chunk 内唯一匹配时补回 block 内容哈希。

    某些 Provider 会把 ``p003-b0070-8011a28964`` 缩写成
    ``p003-b0070``，或正确保留页码/顺序但改写哈希后缀。页码和
    block 顺序在同一论文中是稳定且唯一的，因此可以从当前 chunk
    的可信 block 列表恢复完整 ID。无法唯一定位、跨 chunk 或格式
    不合法的引用保持原样，继续由后续严格校验拒绝。
    """

    allowed_by_locator: dict[str, list[str]] = {}
    for block_id in chunk.block_ids:
        if block_id not in blocks_by_id:
            continue
        locator = _block_locator(block_id)
        if locator is not None:
            allowed_by_locator.setdefault(locator, []).append(block_id)

    canonical: list[str] = []
    for requested_id in requested_ids:
        resolved_id = requested_id
        if requested_id not in blocks_by_id:
            locator = _block_locator(requested_id)
            matches = (
                allowed_by_locator.get(locator, [])
                if locator is not None
                else []
            )
            if len(matches) == 1:
                resolved_id = matches[0]
        if resolved_id not in canonical:
            canonical.append(resolved_id)
    return canonical


def resolve_evidence(
    *,
    draft: EvidenceDraft,
    document: PaperDocument,
    section: PaperSection,
    chunk: SectionChunk,
    blocks_by_id: dict[str, PaperBlock],
) -> PaperEvidence:
    """验证 block 引用并补齐不可由 LLM 生成的来源字段。"""

    allowed_ids = set(chunk.block_ids)
    requested_ids = _canonical_block_ids(
        list(dict.fromkeys(draft.block_ids)),
        chunk=chunk,
        blocks_by_id=blocks_by_id,
    )

    unknown_ids = [
        block_id
        for block_id in requested_ids
        if block_id not in blocks_by_id
    ]
    outside_ids = [
        block_id
        for block_id in requested_ids
        if block_id in blocks_by_id and block_id not in allowed_ids
    ]

    if unknown_ids:
        raise InvalidEvidenceReference(
            f"Unknown evidence block_ids: {unknown_ids}"
        )
    if outside_ids:
        raise InvalidEvidenceReference(
            "Evidence block_ids are outside the current section chunk: "
            f"{outside_ids}"
        )

    resolved_blocks = [blocks_by_id[block_id] for block_id in requested_ids]
    if not resolved_blocks:
        raise InvalidEvidenceReference("Evidence must reference at least one block")

    text = "\n".join(block.text for block in resolved_blocks)
    content_hash = _sha256(text)
    page_start = min(block.page for block in resolved_blocks)
    page_end = max(block.page for block in resolved_blocks)
    evidence_seed = (
        f"{document.document_id}|{section.section_id}|"
        f"{','.join(requested_ids)}|{content_hash}"
    )

    return PaperEvidence(
        evidence_id=f"pev-{_sha256(evidence_seed)[:16]}",
        document_id=document.document_id,
        section_id=section.section_id,
        block_ids=requested_ids,
        page_start=page_start,
        page_end=page_end,
        text=text,
        summary=draft.summary,
        content_hash=content_hash,
        confidence=draft.confidence,
    )


def _confidence_label(value: float) -> Confidence:
    if value >= 0.85:
        return "high"
    if value >= 0.60:
        return "medium"
    return "low"


def to_legacy_evidence(
    paper_evidence: PaperEvidence,
    *,
    source_path: str,
    section_title: str,
) -> Evidence:
    """转换为当前 PaperSummary 使用的兼容 Evidence。"""

    if paper_evidence.page_start == paper_evidence.page_end:
        page_label = f"page {paper_evidence.page_start}"
    else:
        page_label = (
            f"pages {paper_evidence.page_start}-{paper_evidence.page_end}"
        )

    return Evidence(
        source_type="paper",
        source_path=source_path,
        location=f"{section_title}, {page_label}",
        quote_or_summary=paper_evidence.summary,
        confidence=_confidence_label(paper_evidence.confidence),
        evidence_id=paper_evidence.evidence_id,
        document_id=paper_evidence.document_id,
        section_id=paper_evidence.section_id,
        page_start=paper_evidence.page_start,
        page_end=paper_evidence.page_end,
        block_ids=paper_evidence.block_ids,
        content_hash=paper_evidence.content_hash,
    )


def validate_extraction_identity(
    extraction: SectionExtractionDraft,
    chunk: SectionChunk,
) -> None:
    if extraction.section_id != chunk.section_id:
        raise ValueError(
            "Structured output returned a different section_id: "
            f"{extraction.section_id!r}"
        )
    if extraction.chunk_id != chunk.chunk_id:
        raise ValueError(
            "Structured output returned a different chunk_id: "
            f"{extraction.chunk_id!r}"
        )

def iter_extraction_evidence_drafts(
    extraction: SectionExtractionDraft,
) -> Iterator[EvidenceDraft]:
    """统一遍历 SectionExtractionDraft 中所有 EvidenceDraft。"""

    for item in extraction.research_problem_candidates:
        yield item.evidence
    for item in extraction.core_idea_candidates:
        yield item.evidence
    for item in extraction.method_modules:
        yield item.evidence
    for item in extraction.datasets:
        yield item.evidence
    for item in extraction.metrics:
        yield item.evidence
    for item in extraction.experiment_settings:
        yield item.evidence
    for item in extraction.reproduction_risks:
        yield item.evidence


def validate_extraction_evidence_references(
    *,
    extraction: SectionExtractionDraft,
    chunk: SectionChunk,
    blocks_by_id: dict[str, PaperBlock],
) -> None:
    """在写缓存前验证全部 block_id 存在且属于当前 chunk。"""

    allowed_ids = set(chunk.block_ids)

    for draft in iter_extraction_evidence_drafts(extraction):
        requested_ids = _canonical_block_ids(
            list(dict.fromkeys(draft.block_ids)),
            chunk=chunk,
            blocks_by_id=blocks_by_id,
        )
        # 缓存和后续 reducer 必须只看到规范化后的完整 block ID。
        draft.block_ids = requested_ids
        unknown_ids = [
            block_id
            for block_id in requested_ids
            if block_id not in blocks_by_id
        ]
        outside_ids = [
            block_id
            for block_id in requested_ids
            if block_id in blocks_by_id
            and block_id not in allowed_ids
        ]

        if unknown_ids:
            raise InvalidEvidenceReference(
                f"Unknown evidence block_ids: {unknown_ids}"
            )
        if outside_ids:
            raise InvalidEvidenceReference(
                "Evidence block_ids are outside the current chunk: "
                f"{outside_ids}"
            )
