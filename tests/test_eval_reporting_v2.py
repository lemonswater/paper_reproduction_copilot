from __future__ import annotations

from datetime import datetime, timezone

from app.evaluation.reporting import render_eval_report
from app.evaluation.schemas import (
    EvalAssertion,
    EvalCaseResult,
    EvalSuiteResult,
    ScorerResult,
)


def test_report_contains_failed_assertion_diff() -> None:
    result = EvalSuiteResult(
        eval_id="eval_001",
        suite="offline",
        passed=False,
        overall_score=0.0,
        case_results=[
            EvalCaseResult(
                case_id="route_case",
                suite="offline",
                runner="route_function",
                passed=False,
                overall_score=0.0,
                scorer_results=[
                    ScorerResult(
                        category="route",
                        score=0.0,
                        passed=False,
                        assertions=[
                            EvalAssertion(
                                code="ROUTE_EXACT",
                                passed=False,
                                message="route mismatch",
                                expected=[
                                    "executor",
                                    "log_debug",
                                ],
                                actual=[
                                    "executor",
                                    "final_report",
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    text = render_eval_report(result, None)

    assert "ROUTE_EXACT" in text
    assert "log_debug" in text
    assert "final_report" in text
