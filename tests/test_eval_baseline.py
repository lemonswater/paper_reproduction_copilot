from __future__ import annotations

from datetime import datetime, timezone

from app.evaluation.baseline import (
    build_baseline,
    compare_baseline,
)
from app.evaluation.schemas import (
    EvalBaseline,
    EvalCase,
    EvalCaseResult,
    EvalSuiteResult,
)


def _case(
    max_regression: float = 0.0,
    *,
    case_id: str = "case_a",
) -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": case_id,
            "description": "baseline case",
            "suite": "offline",
            "runner": "route_function",
            "categories": ["route"],
            "input": {
                "route_name": "route_after_executor",
                "source_node": "executor",
                "state": {},
            },
            "expected": {
                "exact_route": ["executor", "final_report"],
            },
            "thresholds": {
                "max_score_regression": max_regression,
            },
        }
    )


def _suite(
    score: float,
    passed: bool,
    *,
    case_id: str = "case_a",
) -> EvalSuiteResult:
    return EvalSuiteResult(
        eval_id="eval_fixture",
        suite="offline",
        passed=passed,
        overall_score=score,
        case_results=[
            EvalCaseResult(
                case_id=case_id,
                suite="offline",
                runner="route_function",
                passed=passed,
                overall_score=score,
            )
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def test_baseline_detects_new_failure_and_score_regression() -> None:
    baseline = build_baseline(_suite(1.0, True))
    current = _suite(0.5, False)

    diff = compare_baseline(
        baseline=baseline,
        current=current,
        cases_by_id={"case_a": _case()},
    )

    assert diff.passed is False
    assert diff.newly_failed_cases == ["case_a"]
    assert diff.score_regressions[0]["delta"] == -0.5


def test_small_allowed_regression_can_pass() -> None:
    baseline = build_baseline(_suite(1.0, True))
    current = _suite(0.96, True)

    diff = compare_baseline(
        baseline=baseline,
        current=current,
        cases_by_id={
            "case_a": _case(max_regression=0.05),
        },
    )

    assert diff.passed is True


def test_missing_and_new_cases_are_reported() -> None:
    baseline = build_baseline(_suite(1.0, True))
    current = _suite(1.0, True, case_id="case_b")

    diff = compare_baseline(
        baseline=baseline,
        current=current,
        cases_by_id={"case_b": _case(case_id="case_b")},
    )

    assert diff.passed is False
    assert diff.missing_cases == ["case_a"]
    assert diff.new_cases == ["case_b"]


def test_new_case_alone_is_not_a_regression() -> None:
    baseline = EvalBaseline(
        suite="offline",
        cases=[],
    )
    current = _suite(1.0, True, case_id="case_b")

    diff = compare_baseline(
        baseline=baseline,
        current=current,
        cases_by_id={"case_b": _case(case_id="case_b")},
    )

    assert diff.passed is True
    assert diff.new_cases == ["case_b"]
