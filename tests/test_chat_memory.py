from __future__ import annotations

from pathlib import Path

import pytest

from app.chat.errors import ChatMemoryConflict
from app.chat.memory import (
    ConversationMemoryCompactor,
    MemoryDraftResult,
    validate_memory_hash,
)
from app.chat.schemas import (
    ChatCitation,
    MemoryDraft,
    MemoryStatement,
)
from app.chat.store import SqliteChatRepository


def repository_with_exchanges(
    tmp_path: Path,
    count: int,
) -> SqliteChatRepository:
    repository = SqliteChatRepository(tmp_path / "chat.sqlite")
    repository.initialize()
    citation = ChatCitation(
        citation_id="artifact:report:1",
        source_type="artifact",
        label="reports/final_report.md",
        artifact_id="report",
        relative_path="reports/final_report.md",
        artifact_sha256="a" * 64,
        locator="chunk 1",
    )
    for index in range(count):
        repository.append_exchange(
            job_id="job-1",
            idempotency_key=f"ask-{index}",
            request_sha256=f"{index + 1:064x}",
            question=(
                "Only use CPU in later discussion"
                if index == 0
                else f"question {index}"
            ),
            answer=f"answer {index}",
            citations=([citation] if index == 0 else []),
        )
    return repository


def compactor(repository, invoker):
    def routed_invoker(prompt: str, job_id: str) -> MemoryDraftResult:
        del job_id
        return MemoryDraftResult(
            draft=invoker(prompt),
            model_name="fake-model",
            model_invocation_id=None,
        )

    return ConversationMemoryCompactor(
        repository=repository,
        invoker=routed_invoker,
        enabled=True,
        recent_messages=4,
        min_messages=4,
        max_messages=20,
        max_input_chars=20000,
        memory_max_chars=8000,
        prompt_version="phase36-test",
        model_name="fake-model",
        structured_method="json_schema",
        strict=True,
    )


def test_compaction_creates_hashed_memory_without_deleting_raw_messages(
    tmp_path,
):
    repository = repository_with_exchanges(tmp_path, count=5)

    def invoke(_prompt: str) -> MemoryDraft:
        return MemoryDraft(
            summary="The user constrained later discussion to CPU.",
            user_constraints=[
                MemoryStatement(
                    text="Only use CPU.",
                    source_sequences=[1],
                )
            ],
            citation_ids_to_preserve=["artifact:report:1"],
        )

    outcome = compactor(repository, invoke).ensure_memory("job-1")

    assert outcome.created is True
    assert outcome.degraded is False
    assert outcome.memory is not None
    assert outcome.memory.covered_from_sequence == 1
    assert outcome.memory.covered_through_sequence == 6
    validate_memory_hash(outcome.memory)
    assert outcome.memory.body.citation_anchors[0].artifact_id == "report"
    assert repository.latest_sequence("job-1") == 10
    assert len(repository.list_messages(
        job_id="job-1",
        after_sequence=0,
        limit=20,
    )) == 10


def test_unknown_memory_sources_degrade_to_previous_memory(tmp_path):
    repository = repository_with_exchanges(tmp_path, count=4)

    invalid = compactor(
        repository,
        lambda _prompt: MemoryDraft(
            summary="invented",
            user_constraints=[
                MemoryStatement(
                    text="Invented constraint",
                    source_sequences=[999],
                )
            ],
            citation_ids_to_preserve=["artifact:invented:1"],
        ),
    ).ensure_memory("job-1")

    assert invalid.created is False
    assert invalid.degraded is True
    assert invalid.memory is None
    assert repository.get_latest_memory("job-1") is None


def test_second_compaction_links_to_first_memory(tmp_path):
    repository = repository_with_exchanges(tmp_path, count=5)

    def first(_prompt: str) -> MemoryDraft:
        return MemoryDraft(
            summary="CPU constraint",
            user_constraints=[
                MemoryStatement(text="Only CPU", source_sequences=[1])
            ],
        )

    first_outcome = compactor(repository, first).ensure_memory("job-1")
    assert first_outcome.memory is not None
    second_delta_user_sequence = (
        first_outcome.memory.covered_through_sequence + 1
    )

    for index in range(5, 8):
        repository.append_exchange(
            job_id="job-1",
            idempotency_key=f"ask-{index}",
            request_sha256=f"{index + 1:064x}",
            question=f"question {index}",
            answer=f"answer {index}",
            citations=[],
        )

    def second(_prompt: str) -> MemoryDraft:
        return MemoryDraft(
            summary="CPU constraint remains; small validation was chosen.",
            user_constraints=[
                MemoryStatement(text="Only CPU", source_sequences=[1])
            ],
            decisions=[
                MemoryStatement(
                    text="Validate with a small run first.",
                    source_sequences=[second_delta_user_sequence],
                )
            ],
        )

    second_outcome = compactor(repository, second).ensure_memory("job-1")
    assert second_outcome.memory is not None
    assert second_outcome.memory.version == 2
    assert second_outcome.memory.parent_memory_id == first_outcome.memory.memory_id
    assert (
        second_outcome.memory.parent_memory_sha256
        == first_outcome.memory.memory_sha256
    )
    validate_memory_hash(second_outcome.memory)


def test_memory_provider_failure_does_not_delete_or_block_history(tmp_path):
    repository = repository_with_exchanges(tmp_path, count=4)

    def fail(_prompt: str):
        raise RuntimeError("provider unavailable")

    outcome = compactor(repository, fail).ensure_memory("job-1")
    assert outcome.degraded is True
    assert outcome.memory is None
    assert repository.latest_sequence("job-1") == 8


def test_memory_hash_detects_body_tampering(tmp_path):
    repository = repository_with_exchanges(tmp_path, count=5)
    outcome = compactor(
        repository,
        lambda _prompt: MemoryDraft(summary="Original summary."),
    ).ensure_memory("job-1")
    assert outcome.memory is not None

    tampered_body = outcome.memory.body.model_copy(
        update={"summary": "Tampered summary."}
    )
    tampered = outcome.memory.model_copy(
        update={"body": tampered_body}
    )

    with pytest.raises(ChatMemoryConflict):
        validate_memory_hash(tampered)


from app.chat.memory import build_memory_draft_invoker


@pytest.mark.provider
def test_memory_provider_returns_bounded_structured_draft():
    prompt = """
你是会话记忆压缩器，只返回符合 MemoryDraft schema 的结构化对象。

AVAILABLE_SEQUENCES:
[1,2]

AVAILABLE_CITATION_IDS:
["job:current"]

DELTA_MESSAGES:
[
  {"sequence":1,"role":"user","content":"只使用 CPU 做最小验证。","citation_ids":[]},
  {"sequence":2,"role":"assistant","content":"已记录该限制。","citation_ids":["job:current"]}
]

不要返回 version、hash、memory_id 或完整 citation 对象。
""".strip()

    draft = build_memory_draft_invoker()(prompt, "job-provider-probe").draft

    assert draft.summary.strip()
    assert {
        sequence
        for item in [
            *draft.user_constraints,
            *draft.decisions,
            *draft.open_questions,
        ]
        for sequence in item.source_sequences
    } <= {1, 2}
    assert set(draft.citation_ids_to_preserve) <= {"job:current"}


from app.chat.memory import _memory_body_hash_payload
from app.chat.schemas import ChatCitation, ConversationMemoryBody


def test_phase36_memory_hash_projection_ignores_new_comparison_fields() -> None:
    legacy = ConversationMemoryBody(
        summary="legacy memory",
        citation_anchors=[
            ChatCitation(
                citation_id="job:current",
                source_type="job",
                label="Current job",
            )
        ],
    )
    payload = _memory_body_hash_payload(legacy)

    assert "citation_schema_version" not in payload
    anchor = payload["citation_anchors"][0]
    assert "comparison_id" not in anchor
    assert "comparison_hash" not in anchor


def test_phase38_memory_hash_projection_binds_comparison_identity() -> None:
    current = ConversationMemoryBody(
        summary="comparison memory",
        citation_schema_version="phase38-v2",
        citation_anchors=[
            ChatCitation(
                citation_id="comparison:comparison_aaaaaaaaaaaaaaaaaaaaaaaa",
                source_type="comparison",
                label="Run comparison",
                comparison_id="comparison_aaaaaaaaaaaaaaaaaaaaaaaa",
                comparison_hash="a" * 64,
                base_job_id="job-base",
                target_job_id="job-target",
            )
        ],
    )
    payload = _memory_body_hash_payload(current)

    assert payload["citation_schema_version"] == "phase38-v2"
    anchor = payload["citation_anchors"][0]
    assert anchor["comparison_hash"] == "a" * 64
    assert anchor["base_job_id"] == "job-base"
