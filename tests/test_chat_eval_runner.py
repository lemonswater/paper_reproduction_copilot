from __future__ import annotations

from pathlib import Path

import pytest

from app.evaluation import chat_runner
from app.evaluation.chat_schemas import ChatEvalScenario
from app.evaluation.schemas import EvalCase


def _case(case_id: str = "chat-runner") -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": case_id,
            "description": "chat runner",
            "suite": "chat_offline",
            "runner": "chat_scenario",
            "categories": ["evidence", "quality"],
            "input": {
                "fixture_path": "fixtures/chat/unused.json"
            },
            "expected": {
                "chat_turns": [
                    {
                        "label": "turn-1",
                        "expected_refusal": True,
                        "allowed_citation_ids": [],
                    }
                ]
            },
        }
    )


def _unknown_citation_scenario() -> ChatEvalScenario:
    return ChatEvalScenario.model_validate(
        {
            "scenario_id": "chat-runner",
            "sources": [
                {
                    "citation": {
                        "citation_id": "job:current",
                        "source_type": "job",
                        "label": "Current job state",
                    },
                    "content": "status=running",
                }
            ],
            "turns": [
                {
                    "label": "turn-1",
                    "question": "Did you execute it?",
                    "idempotency_key": "turn-1",
                    "scripted_draft": {
                        "answer": "I executed it.",
                        "citation_ids": ["artifact:unknown:1"],
                    },
                }
            ],
            "compaction_enabled": False,
        }
    )


def test_offline_runner_uses_real_service_citation_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    scenario = _unknown_citation_scenario()
    monkeypatch.setattr(
        chat_runner,
        "_load_scenario",
        lambda _case: scenario,
    )

    observation = chat_runner.run_chat_eval_case(
        _case(),
        work_dir=tmp_path / "case",
        provider=False,
    )

    assert observation.chat is not None
    run = observation.chat.runs[0]
    turn = run.turns[0]
    assert turn.requested_citation_ids == ["artifact:unknown:1"]
    assert turn.unknown_requested_citation_ids == [
        "artifact:unknown:1"
    ]
    assert turn.citation_ids == []
    assert turn.refused is True
    assert run.answer_invocations == 1
    assert run.memory_invocations == 0
    assert not (tmp_path / "case" / "_chat_scratch").exists()


def test_offline_runner_creates_valid_memory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    scenario = ChatEvalScenario.model_validate(
        {
            "scenario_id": "chat-runner",
            "sources": [
                {
                    "citation": {
                        "citation_id": "job:current",
                        "source_type": "job",
                        "label": "Current job state",
                    },
                    "content": "status=running",
                }
            ],
            "seed_exchanges": [
                {
                    "question": "Only CPU.",
                    "answer": "Acknowledged.",
                    "citation_ids": ["job:current"],
                },
                {
                    "question": "filler",
                    "answer": "filler answer",
                    "citation_ids": ["job:current"],
                },
                {
                    "question": "recent",
                    "answer": "recent answer",
                    "citation_ids": ["job:current"],
                },
            ],
            "turns": [
                {
                    "label": "turn-1",
                    "question": "status?",
                    "idempotency_key": "turn-1",
                    "scripted_draft": {
                        "answer": "running",
                        "citation_ids": ["job:current"],
                    },
                }
            ],
            "memory_scripts": [
                {
                    "draft": {
                        "summary": "Only CPU.",
                        "user_constraints": [
                            {
                                "text": "Only CPU.",
                                "source_sequences": [1],
                            }
                        ],
                        "citation_ids_to_preserve": ["job:current"],
                    }
                }
            ],
            "recent_messages": 2,
            "compaction_min_messages": 4,
        }
    )
    monkeypatch.setattr(
        chat_runner,
        "_load_scenario",
        lambda _case: scenario,
    )

    observation = chat_runner.run_chat_eval_case(
        _case(),
        work_dir=tmp_path / "memory-case",
        provider=False,
    )

    assert observation.chat is not None
    run = observation.chat.runs[0]
    assert run.memory.available is True
    assert run.memory.hash_valid is True
    assert run.memory.source_sequence_valid_ratio == 1.0
    assert run.memory.user_constraints[0].source_sequences == [1]


def test_provider_mode_rejects_scripted_draft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    scenario = _unknown_citation_scenario().model_copy(
        update={"repetitions": 1}
    )
    provider_case = EvalCase.model_validate(
        {
            "case_id": "chat-runner",
            "description": "provider runner",
            "suite": "chat_provider",
            "runner": "chat_provider",
            "categories": ["quality"],
            "input": {
                "fixture_path": "fixtures/chat/unused.json"
            },
            "expected": {
                "chat_turns": [
                    {
                        "label": "turn-1",
                        "expected_refusal": True,
                    }
                ]
            },
        }
    )
    monkeypatch.setattr(
        chat_runner,
        "_load_scenario",
        lambda _case: scenario,
    )

    with pytest.raises(ValueError, match="禁止 scripted"):
        chat_runner.run_chat_eval_case(
            provider_case,
            work_dir=tmp_path / "provider-case",
            provider=True,
        )
