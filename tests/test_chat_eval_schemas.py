from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.evaluation.chat_schemas import ChatEvalScenario
from app.evaluation.schemas import EvalCase
from app.evaluation.case_loader import load_cases


def _case(*, suite="chat_offline", runner="chat_scenario"):
    return {
        "case_id": "chat-case",
        "description": "chat case",
        "suite": suite,
        "runner": runner,
        "categories": ["quality"],
        "input": {"fixture_path": "fixtures/chat/case.json"},
        "expected": {
            "chat_turns": [
                {
                    "label": "turn-1",
                    "expected_refusal": True,
                }
            ]
        },
    }


def _scenario():
    return {
        "scenario_id": "chat-case",
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
                "question": "What is the status?",
                "idempotency_key": "turn-1",
                "scripted_draft": {
                    "answer": "running",
                    "citation_ids": ["job:current"],
                },
            }
        ],
        "compaction_enabled": False,
    }


def test_chat_offline_case_requires_matching_runner_and_suite():
    case = EvalCase.model_validate(_case())

    assert case.runner == "chat_scenario"
    assert case.suite == "chat_offline"


def test_chat_runner_in_wrong_suite_is_rejected():
    with pytest.raises(ValidationError, match="chat_offline"):
        EvalCase.model_validate(
            _case(suite="offline", runner="chat_scenario")
        )


def test_chat_case_requires_a_chat_oracle():
    payload = _case()
    payload["expected"] = {}

    with pytest.raises(ValidationError, match="Chat Oracle"):
        EvalCase.model_validate(payload)


def test_chat_oracle_rejects_blank_terms():
    payload = _case()
    payload["expected"]["chat_turns"][0][
        "required_answer_terms"
    ] = [" "]

    with pytest.raises(ValidationError, match="空字符串"):
        EvalCase.model_validate(payload)


def test_required_citation_must_belong_to_allowlist():
    payload = _case()
    payload["expected"]["chat_turns"][0].update(
        {
            "required_citation_ids": ["job:current"],
            "allowed_citation_ids": [],
        }
    )

    with pytest.raises(ValidationError, match="必须属于 allowlist"):
        EvalCase.model_validate(payload)


def test_scenario_requires_job_current_as_first_source():
    payload = _scenario()
    payload["sources"][0]["citation"]["citation_id"] = "job:other"

    with pytest.raises(ValidationError, match="job:current"):
        ChatEvalScenario.model_validate(payload)


def test_scenario_rejects_unknown_seed_citation():
    payload = _scenario()
    payload["seed_exchanges"] = [
        {
            "question": "q",
            "answer": "a",
            "citation_ids": ["artifact:unknown:1"],
        }
    ]

    with pytest.raises(ValidationError, match="未知 citation"):
        ChatEvalScenario.model_validate(payload)


def test_memory_script_requires_draft_xor_error():
    payload = _scenario()
    payload["memory_scripts"] = [
        {
            "draft": {"summary": "summary"},
            "error_code": "provider_unavailable",
        }
    ]

    with pytest.raises(ValidationError, match="且只能"):
        ChatEvalScenario.model_validate(payload)


def test_repository_chat_offline_cases_are_valid():
    cases = load_cases(suite="chat_offline")

    assert {item.runner for item in cases} == {"chat_scenario"}
    assert len(cases) >= 3


def test_repository_chat_provider_cases_are_valid_and_isolated():
    cases = load_cases(suite="chat_provider")

    assert {item.runner for item in cases} == {"chat_provider"}
    assert len(cases) >= 4
    assert any(
        item.case_id == "chat_provider_run_comparison_explanation"
        for item in cases
    )
