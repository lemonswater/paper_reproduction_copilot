from __future__ import annotations

import hashlib

from app.paper.chunking import chunk_section
from app.paper.schemas import PaperBlock, PaperSection


def _block(block_id: str, order: int, text: str) -> PaperBlock:
    return PaperBlock(
        block_id=block_id,
        page=14,
        order=order,
        block_type="paragraph",
        text=text,
        text_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


def test_chunking_never_splits_or_loses_a_block() -> None:
    blocks = [
        _block("b1", 0, "A" * 60),
        _block("b2", 1, "B" * 60),
        _block("b3", 2, "C" * 60),
    ]
    section = PaperSection(
        section_id="sec-impl",
        number="C",
        title="Implementation Details",
        normalized_title="implementation details",
        level=1,
        kind="implementation",
        page_start=14,
        page_end=14,
        block_ids=["b1", "b2", "b3"],
        content_hash="section-hash",
    )

    chunks = chunk_section(
        section,
        {block.block_id: block for block in blocks},
        target_chars=100,
    )

    actual_ids = [
        block_id
        for chunk in chunks
        for block_id in chunk.block_ids
    ]
    assert actual_ids == ["b1", "b2", "b3"]
    assert all(
        block.text in "\n".join(chunk.text for chunk in chunks)
        for block in blocks
    )