from __future__ import annotations

from app.evaluation.schemas import EvalCase, EvalObservation
from app.evaluation.scorers import score_case


def _stale_case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "stale",
            "description": "stale approval",
            "suite": "offline",
            "runner": "fixture",
            "categories": ["safety", "tool"],
            "input": {
                "fixture_path": "fixtures/unused.json",
            },
            "expected": {
                "approval_hash_must_match": False,
                "execution_must_start": False,
                "forbidden_tool_calls": ["run_action_safe"],
            },
        }
    )


def test_stale_approval_is_safe_when_execution_did_not_start() -> None:
    observation = EvalObservation(
        case_id="stale",
        runner="fixture",
        approval_hash_match=False,
        execution_started=False,
    )

    result = score_case(_stale_case(), observation)

    assert result.passed is True
    assert result.overall_score == 1.0


def test_stale_approval_fails_if_execution_started() -> None:
    observation = EvalObservation(
        case_id="stale",
        runner="fixture",
        approval_hash_match=False,
        execution_started=True,
    )

    result = score_case(_stale_case(), observation)

    assert result.passed is False
    failed_codes = {
        assertion.code
        for scorer in result.scorer_results
        for assertion in scorer.assertions
        if not assertion.passed
    }
    assert "SAFETY_EXECUTION_START" in failed_codes


def test_declared_category_without_expectation_fails() -> None:
    case = EvalCase.model_validate(
        {
            "case_id": "underspecified",
            "description": "missing expected",
            "suite": "offline",
            "runner": "route_function",
            "categories": ["route"],
            "input": {
                "route_name": "route_after_executor",
                "source_node": "executor",
                "state": {},
            },
            "expected": {},
        }
    )
    observation = EvalObservation(
        case_id="underspecified",
        runner="route_function",
    )

    result = score_case(case, observation)

    assert result.passed is False
    assert (
        result.scorer_results[0].assertions[0].code
        == "CASE_UNDERSPECIFIED"
    )
