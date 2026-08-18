from __future__ import annotations

from app.evaluation.reporting import render_eval_report
from app.evaluation.schemas import (
    EvalAssertion,
    EvalCase,
    EvalCaseResult,
    EvalObservation,
    EvalSuiteResult,
    ScorerResult,
)
from app.evaluation.scorers import score_case


def test_quality_scorer_reads_observation_payload() -> None:
    case = EvalCase(
        case_id="mapping_quality",
        description="mapping quality fixture",
        runner="fixture",
        categories=["quality"],
        input={"fixture_path": "fixtures/mapping.json"},
        expected={
            "required_files": ["models/encoder.py"],
            "forbidden_claims": ["models/decoder.py"],
        },
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="fixture",
        output_payloads={
            "analysis/paper_code_mapping.json": [
                {"file_path": "models/encoder.py"}
            ]
        },
    )

    result = score_case(
        case,
        observation,
    )

    assert result.passed is True
    assert result.overall_score == 1.0
    assert all(
        assertion.passed
        for scorer in result.scorer_results
        for assertion in scorer.assertions
    )


def _case_result(case_id: str, passed: bool) -> EvalCaseResult:
    score = 1.0 if passed else 0.0
    return EvalCaseResult(
        case_id=case_id,
        suite="offline",
        runner="fixture",
        passed=passed,
        overall_score=score,
        scorer_results=[
            ScorerResult(
                category="quality",
                score=score,
                passed=passed,
                assertions=[
                    EvalAssertion(
                        code="QUALITY_FIXTURE",
                        passed=passed,
                        message="fixture result",
                        expected=True,
                        actual=passed,
                    )
                ],
            )
        ],
    )


def test_render_eval_report_contains_summary_and_case_details() -> None:
    result = EvalSuiteResult(
        eval_id="eval-report-fixture",
        suite="offline",
        passed=False,
        overall_score=0.5,
        case_results=[
            _case_result("case_success", True),
            _case_result("case_fail", False),
        ],
        category_scores={"quality": 0.5},
        problem_coverage={"7": ["case_success", "case_fail"]},
        generated_at="2026-07-27T00:00:00+00:00",
    )

    text = render_eval_report(result, diff=None)

    assert "# Agent Evaluation Report" in text
    assert "## Summary" in text
    assert "Cases：`1/2`" in text
    assert "### case_success" in text
    assert "### case_fail" in text
    assert "`FAIL` `QUALITY_FIXTURE`" in text
