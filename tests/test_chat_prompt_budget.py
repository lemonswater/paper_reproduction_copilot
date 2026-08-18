from __future__ import annotations

import json

import pytest

from app.chat.context import GroundingBundle, GroundingSource
from app.chat.errors import (
    ChatConflictError,
    ChatPromptBudgetExceeded,
)
from app.chat.prompt import (
    _history_item,
    build_budgeted_chat_prompt,
)
from app.chat.schemas import ChatCitation, ChatMessage
from tests.helpers.interaction import make_job


def message_pair(index: int, content_chars: int = 120):
    user_sequence = index * 2 + 1
    user_id = f"user-{index}"
    user = ChatMessage(
        message_id=user_id,
        job_id="job-1",
        sequence=user_sequence,
        role="user",
        content=f"question-{index}-" + "q" * content_chars,
        created_at="2026-08-08T00:00:00+00:00",
    )
    assistant = ChatMessage(
        message_id=f"assistant-{index}",
        job_id="job-1",
        sequence=user_sequence + 1,
        role="assistant",
        content=f"answer-{index}-" + "a" * content_chars,
        reply_to=user_id,
        created_at="2026-08-08T00:00:01+00:00",
    )
    return user, assistant


def source(
    citation_id: str,
    *,
    content: str,
    source_type: str = "job",
) -> GroundingSource:
    return GroundingSource(
        citation=ChatCitation(
            citation_id=citation_id,
            source_type=source_type,
            label=citation_id,
        ),
        content=content,
        score=100,
    )


def bundle(*extra: GroundingSource) -> GroundingBundle:
    return GroundingBundle(
        job=make_job(),
        sources=[
            source(
                "job:current",
                content="status=running; stage=experiment",
            ),
            *extra,
        ],
    )


def test_history_budget_keeps_complete_newest_exchange():
    pairs = [message_pair(index) for index in range(3)]
    history = [item for pair in pairs for item in pair]
    newest_pair_chars = len(
        json.dumps(
            [_history_item(item) for item in pairs[-1]],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )

    result = build_budgeted_chat_prompt(
        question="What did we decide?",
        history=history,
        memory=None,
        bundle=bundle(),
        prompt_max_chars=8000,
        history_max_chars=newest_pair_chars + 10,
        memory_max_chars=2000,
    )

    assert [item.sequence for item in result.history] == [5, 6]
    assert result.history[0].role == "user"
    assert result.history[1].reply_to == result.history[0].message_id


def test_oversized_optional_source_is_not_in_prompt_or_whitelist():
    oversized = source(
        "artifact:large:1",
        source_type="artifact",
        content="x" * 20000,
    )

    result = build_budgeted_chat_prompt(
        question="What is the status?",
        history=[],
        memory=None,
        bundle=bundle(oversized),
        prompt_max_chars=5000,
        history_max_chars=1000,
        memory_max_chars=2000,
    )

    assert {
        item.citation.citation_id for item in result.sources
    } == {"job:current"}
    assert "artifact:large:1" not in result.prompt


def test_malformed_history_is_rejected_instead_of_silently_sliced():
    user, _assistant = message_pair(0)

    with pytest.raises(ChatConflictError):
        build_budgeted_chat_prompt(
            question="Why?",
            history=[user],
            memory=None,
            bundle=bundle(),
            prompt_max_chars=5000,
            history_max_chars=1000,
            memory_max_chars=2000,
        )


def test_too_small_budget_fails_closed():
    with pytest.raises(ChatPromptBudgetExceeded):
        build_budgeted_chat_prompt(
            question="q" * 4000,
            history=[],
            memory=None,
            bundle=bundle(),
            prompt_max_chars=100,
            history_max_chars=1000,
            memory_max_chars=2000,
        )
