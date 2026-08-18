from __future__ import annotations

import hashlib

from app.paper.schemas import PaperBlock, PaperSection, SectionChunk

_SECTION_PRIORITY = {
    "implementation": 0,
    "experiments": 1,
    "datasets": 2,
    "ablation": 3,
    "method": 4,
    "abstract": 5,
    "introduction": 6,
    "results": 7,
    "limitations": 8,
    "conclusion": 9,
    "appendix": 10,
    "other": 11,
    "related_work": 12,
    "references": 99,
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _render_block(block: PaperBlock) -> str:
    """把来源 ID 和页码放进 prompt 文本。"""

    return f"[{block.block_id}][page {block.page}] {block.text}"


def chunk_section(
    section: PaperSection,
    blocks_by_id: dict[str, PaperBlock],
    *,
    target_chars: int,
) -> list[SectionChunk]:
    """按完整 block 将一个 section 切成一个或多个 chunk。"""

    if target_chars <= 0:
        raise ValueError("target_chars must be positive")

    source_blocks = [
        blocks_by_id[block_id]
        for block_id in section.block_ids
        if block_id in blocks_by_id
        and not blocks_by_id[block_id].excluded
    ]
    if not source_blocks:
        return []

    groups: list[list[PaperBlock]] = []
    current: list[PaperBlock] = []
    current_chars = 0

    for block in source_blocks:
        rendered = _render_block(block)

        # 当前组非空且再加入会超限时，先提交当前组。
        # 单个超长 block 不从中间切开，而是单独成为一个 chunk。
        if current and current_chars + len(rendered) > target_chars:
            groups.append(current)
            current = []
            current_chars = 0

        current.append(block)
        current_chars += len(rendered) + 1

    if current:
        groups.append(current)

    chunks: list[SectionChunk] = []
    for index, group in enumerate(groups):
        text = "\n".join(_render_block(block) for block in group)
        content_hash = _sha256(
            "\n".join(block.text_hash for block in group)
        )
        chunk_id = f"{section.section_id}-c{index:03d}-{content_hash[:10]}"

        chunks.append(
            SectionChunk(
                chunk_id=chunk_id,
                section_id=section.section_id,
                section_title=section.title,
                section_kind=section.kind,
                page_start=min(block.page for block in group),
                page_end=max(block.page for block in group),
                block_ids=[block.block_id for block in group],
                text=text,
                content_hash=content_hash,
            )
        )

    return chunks


def build_section_chunks(
    sections: list[PaperSection],
    blocks: list[PaperBlock],
    *,
    target_chars: int,
) -> list[SectionChunk]:
    blocks_by_id = {block.block_id: block for block in blocks}
    return [
        chunk
        for section in sections
        for chunk in chunk_section(
            section,
            blocks_by_id,
            target_chars=target_chars,
        )
    ]


def select_extraction_chunks(
    chunks: list[SectionChunk],
    *,
    max_calls: int,
) -> list[SectionChunk]:
    """在调用预算内优先保留最有复现价值的 section chunk。"""

    if max_calls <= 0:
        return []

    candidates = [
        chunk
        for chunk in chunks
        if chunk.section_kind != "references"
    ]
    candidates.sort(
        key=lambda chunk: (
            _SECTION_PRIORITY.get(chunk.section_kind, 50),
            chunk.page_start,
            chunk.chunk_id,
        )
    )
    return candidates[:max_calls]