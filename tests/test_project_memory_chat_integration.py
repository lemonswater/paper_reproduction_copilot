"""Phase 46: Project Memory Chat Integration 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.chat.context import ChatContextBuilder
from app.chat.schemas import ChatCitation, ConversationMemoryBody
from app.chat.memory import (
    PHASE38_CITATION_FIELDS,
    PHASE46_CITATION_FIELDS,
    _memory_body_hash_payload,
    validate_memory_hash,
)
from app.project_memory.identity import compute_pack_hash
from app.project_memory.schemas import (
    ProjectFactPack,
    ProjectFactPackItem,
    TextFactValue,
)
from tests.helpers.project_memory import NOW, confirmed_fact


def _make_retriever(pack: ProjectFactPack | None):
    retriever = MagicMock()
    retriever.for_job.return_value = pack
    return retriever


def _make_pack(fact=None) -> ProjectFactPack:
    fact = fact or confirmed_fact()
    item = ProjectFactPackItem(
        fact_id=fact.fact_id,
        fact_hash=fact.record_hash,
        category=fact.content.category,
        key=fact.content.key,
        value=fact.content.value,
        source_kind="manual_user",
    )
    draft = ProjectFactPack(
        project_id=fact.project_id,
        project_hash="a" * 64,
        items=[item],
        pack_hash="0" * 64,
        generated_at=NOW,
    )
    payload = draft.model_dump(mode="json")
    payload["pack_hash"] = compute_pack_hash(draft)
    return ProjectFactPack.model_validate(payload)


def test_unbound_job_gets_no_project_fact_sources():
    """未绑定 Job 不会得到 Project Fact source。"""
    retriever = MagicMock()
    retriever.for_job.return_value = None

    builder = ChatContextBuilder(
        interaction=MagicMock(),
        artifact_catalog=MagicMock(),
        artifacts_to_open=3,
        source_limit=10,
        artifact_max_bytes=5000,
        total_context_chars=50000,
        log_max_bytes=5000,
        project_fact_retriever=retriever,
    )

    sources = builder._project_fact_sources(
        job_id="unbound-job",
        keywords=set(),
    )
    assert len(sources) == 0


def test_confirmed_fact_enters_sources():
    """confirmed fact 进入 GroundingSource，citation 包含 project/fact/hash。"""
    pack = _make_pack()
    retriever = _make_retriever(pack)

    builder = ChatContextBuilder(
        interaction=MagicMock(),
        artifact_catalog=MagicMock(),
        artifacts_to_open=3,
        source_limit=10,
        artifact_max_bytes=5000,
        total_context_chars=50000,
        log_max_bytes=5000,
        project_fact_retriever=retriever,
    )

    sources = builder._project_fact_sources(
        job_id="bound-job",
        keywords=set(),
    )
    assert len(sources) == 1
    citation = sources[0].citation
    assert citation.source_type == "project_fact"
    assert citation.project_id == pack.project_id
    assert citation.project_fact_id == pack.items[0].fact_id
    assert citation.project_fact_hash == pack.items[0].fact_hash


def test_project_fact_citation_validates_identity():
    """project_fact citation 必须包含完整身份。"""
    with pytest.raises(ValueError):
        ChatCitation(
            citation_id="project_fact:test",
            source_type="project_fact",
            label="test",
            project_id="project_" + "1" * 24,
            project_fact_id=None,
            project_fact_hash=None,
        )


def test_non_project_fact_citation_rejects_project_fields():
    """非 project_fact citation 不能携带项目事实身份。"""
    with pytest.raises(ValueError):
        ChatCitation(
            citation_id="job:current",
            source_type="job",
            label="test",
            project_id="project_" + "1" * 24,
        )


def test_phase36_memory_hash_still_passes():
    """旧 Phase 36 Memory Hash 仍通过。"""
    body = ConversationMemoryBody(
        summary="test summary",
        citation_schema_version="phase36-v1",
    )
    payload = _memory_body_hash_payload(body)
    # Phase 36 should not have citation_schema_version in the hash
    assert "citation_schema_version" not in payload


def test_phase38_memory_hash_excludes_phase46_fields():
    """Phase 38 Memory Hash 排除 Phase 46 字段。"""
    body = ConversationMemoryBody(
        summary="test summary",
        citation_schema_version="phase38-v2",
    )
    payload = _memory_body_hash_payload(body)
    # Phase 38 should have citation_schema_version but not phase46 fields in citations
    for citation in payload.get("citation_anchors", []):
        for field in PHASE46_CITATION_FIELDS:
            assert field not in citation


def test_phase46_v3_schema_accepts_project_fact_citation():
    """Phase 46 v3 schema 接受 project_fact citation。"""
    fact = confirmed_fact()
    citation = ChatCitation(
        citation_id=f"project_fact:{fact.fact_id}",
        source_type="project_fact",
        label="Project fact: test",
        project_id=fact.project_id,
        project_fact_id=fact.fact_id,
        project_fact_hash=fact.record_hash,
    )
    body = ConversationMemoryBody(
        summary="test summary",
        citation_anchors=[citation],
        citation_schema_version="phase46-v3",
    )
    assert body.citation_schema_version == "phase46-v3"


def test_phase38_rejects_project_fact_citation():
    """Phase 38 v2 不接受 project_fact citation。"""
    fact = confirmed_fact()
    citation = ChatCitation(
        citation_id=f"project_fact:{fact.fact_id}",
        source_type="project_fact",
        label="Project fact: test",
        project_id=fact.project_id,
        project_fact_id=fact.fact_id,
        project_fact_hash=fact.record_hash,
    )
    with pytest.raises(ValueError):
        ConversationMemoryBody(
            summary="test summary",
            citation_anchors=[citation],
            citation_schema_version="phase38-v2",
        )


def test_empty_pack_produces_no_sources():
    """空 Pack 不产生 sources。"""
    draft = ProjectFactPack(
        project_id="project_" + "1" * 24,
        project_hash="a" * 64,
        items=[],
        pack_hash="0" * 64,
        generated_at=NOW,
    )
    payload = draft.model_dump(mode="json")
    payload["pack_hash"] = compute_pack_hash(draft)
    pack = ProjectFactPack.model_validate(payload)

    retriever = _make_retriever(pack)
    builder = ChatContextBuilder(
        interaction=MagicMock(),
        artifact_catalog=MagicMock(),
        artifacts_to_open=3,
        source_limit=10,
        artifact_max_bytes=5000,
        total_context_chars=50000,
        log_max_bytes=5000,
        project_fact_retriever=retriever,
    )

    sources = builder._project_fact_sources(
        job_id="bound-job",
        keywords=set(),
    )
    assert len(sources) == 0
