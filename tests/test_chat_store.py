from __future__ import annotations

import pytest

from app.chat.errors import ChatConflictError
from app.chat.schemas import (
    ChatCitation,
    ConversationMemory,
    ConversationMemoryBody,
)
from app.chat.store import SqliteChatRepository


def _repository(tmp_path) -> SqliteChatRepository:
    repository = SqliteChatRepository(
        tmp_path / "chat.sqlite"
    )
    repository.initialize()
    return repository


def test_exchange_is_atomic_ordered_and_replayable(tmp_path):
    repository = _repository(tmp_path)
    citation = ChatCitation(
        citation_id="artifact:a:1",
        source_type="artifact",
        label="reports/final_report.md",
        artifact_id="a",
        relative_path="reports/final_report.md",
        artifact_sha256="a" * 64,
        locator="chunk 1",
    )

    user, assistant, created = repository.append_exchange(
        job_id="job-1",
        idempotency_key="ask-1",
        request_sha256="b" * 64,
        question="What happened?",
        answer="The run completed.",
        citations=[citation],
    )

    assert created is True
    assert user.sequence == 1
    assert assistant.sequence == 2
    assert assistant.reply_to == user.message_id
    assert assistant.citations == [citation]

    replay_user, replay_assistant, replay_created = (
        repository.append_exchange(
            job_id="job-1",
            idempotency_key="ask-1",
            request_sha256="b" * 64,
            question="What happened?",
            answer="This value must not replace the stored answer.",
            citations=[],
        )
    )
    assert replay_created is False
    assert replay_user == user
    assert replay_assistant == assistant
    assert repository.list_messages(
        job_id="job-1",
        after_sequence=0,
        limit=10,
    ) == [user, assistant]


def test_idempotency_key_reuse_with_other_question_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    repository.append_exchange(
        job_id="job-1",
        idempotency_key="ask-1",
        request_sha256="a" * 64,
        question="first",
        answer="answer",
        citations=[],
    )

    with pytest.raises(ChatConflictError):
        repository.find_exchange(
            job_id="job-1",
            idempotency_key="ask-1",
            request_sha256="b" * 64,
        )


def test_messages_are_isolated_by_job_id(tmp_path):
    repository = _repository(tmp_path)
    repository.append_exchange(
        job_id="job-a",
        idempotency_key="ask-a",
        request_sha256="a" * 64,
        question="question a",
        answer="answer a",
        citations=[],
    )

    assert repository.list_messages(
        job_id="job-b",
        after_sequence=0,
        limit=10,
    ) == []


def test_recent_messages_returns_true_newest_after_200(tmp_path):
    repository = _repository(tmp_path)
    for index in range(105):
        repository.append_exchange(
            job_id="job-1",
            idempotency_key=f"ask-{index}",
            request_sha256=f"{index:064x}",
            question=f"question {index}",
            answer=f"answer {index}",
            citations=[],
        )

    recent = repository.list_recent_messages(
        job_id="job-1",
        limit=12,
    )

    assert [item.sequence for item in recent] == list(range(199, 211))
    assert recent[-1].content == "answer 104"


def test_message_range_is_inclusive_ordered_and_bounded(tmp_path):
    repository = _repository(tmp_path)
    for index in range(3):
        repository.append_exchange(
            job_id="job-1",
            idempotency_key=f"ask-{index}",
            request_sha256=f"{index + 1:064x}",
            question=f"q{index}",
            answer=f"a{index}",
            citations=[],
        )

    rows = repository.list_messages_range(
        job_id="job-1",
        start_sequence=3,
        end_sequence=6,
        limit=10,
    )
    assert [item.sequence for item in rows] == [3, 4, 5, 6]
    assert repository.latest_sequence("job-1") == 6


def test_delete_job_messages_also_deletes_memory_versions(tmp_path):
    repository = _repository(tmp_path)
    repository.append_exchange(
        job_id="job-1",
        idempotency_key="ask-1",
        request_sha256="a" * 64,
        question="question",
        answer="answer",
        citations=[],
    )
    memory = ConversationMemory(
        memory_id="memory-1",
        job_id="job-1",
        version=1,
        covered_from_sequence=1,
        covered_through_sequence=2,
        delta_messages_sha256="b" * 64,
        body=ConversationMemoryBody(summary="A compact summary."),
        memory_sha256="c" * 64,
        prompt_version="phase36-test",
        model_name="fake-model",
        structured_method="json_schema",
        strict=True,
        created_at="2026-08-08T00:00:00+00:00",
    )
    repository.save_memory(
        memory=memory,
        expected_parent_memory_id=None,
    )

    deleted = repository.delete_job_messages("job-1")

    assert deleted == 2
    assert repository.list_messages(
        job_id="job-1",
        after_sequence=0,
        limit=10,
    ) == []
    assert repository.get_latest_memory("job-1") is None
