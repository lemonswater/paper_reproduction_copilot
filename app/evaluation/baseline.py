from __future__ import annotations

from pathlib import Path

from app.evaluation.schemas import (
    BaselineCase,
    BaselineDiff,
    EvalBaseline,
    EvalCase,
    EvalSuiteResult,
)


def _category_scores(case_result) -> dict[str, float]:
    return {
        item.category: item.score
        for item in case_result.scorer_results
    }


def build_baseline(result: EvalSuiteResult) -> EvalBaseline:
    """
    baseline 只保存稳定评分，不保存 run_id、时间、绝对路径和 UUID。
    """

    return EvalBaseline(
        suite=result.suite,
        cases=[
            BaselineCase(
                case_id=item.case_id,
                passed=item.passed,
                overall_score=item.overall_score,
                category_scores=_category_scores(item),
            )
            for item in sorted(
                result.case_results,
                key=lambda value: value.case_id,
            )
        ],
    )


def write_baseline(
    baseline: EvalBaseline,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        baseline.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def load_baseline(path: Path) -> EvalBaseline | None:
    if not path.is_file():
        return None
    return EvalBaseline.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def compare_baseline(
    *,
    baseline: EvalBaseline,
    current: EvalSuiteResult,
    cases_by_id: dict[str, EvalCase],
) -> BaselineDiff:
    """
    新增 case 不是回归；基线 case 消失、新增失败或超过允许降幅才是回归。
    """

    before = {item.case_id: item for item in baseline.cases}
    after = {item.case_id: item for item in current.case_results}

    new_cases = sorted(after.keys() - before.keys())
    missing_cases = sorted(before.keys() - after.keys())
    newly_failed: list[str] = []
    regressions: list[dict] = []

    for case_id in sorted(before.keys() & after.keys()):
        old = before[case_id]
        new = after[case_id]
        if old.passed and not new.passed:
            newly_failed.append(case_id)

        allowed = cases_by_id[case_id].thresholds.max_score_regression
        delta = new.overall_score - old.overall_score
        if delta < -allowed:
            regressions.append(
                {
                    "case_id": case_id,
                    "baseline_score": old.overall_score,
                    "current_score": new.overall_score,
                    "delta": delta,
                    "allowed_regression": allowed,
                }
            )

        current_categories = {
            item.category: item.score
            for item in new.scorer_results
        }
        for category in sorted(
            old.category_scores.keys() & current_categories.keys()
        ):
            category_delta = (
                current_categories[category]
                - old.category_scores[category]
            )
            if category_delta < -allowed:
                regressions.append(
                    {
                        "case_id": case_id,
                        "category": category,
                        "baseline_score": old.category_scores[category],
                        "current_score": current_categories[category],
                        "delta": category_delta,
                        "allowed_regression": allowed,
                    }
                )

    return BaselineDiff(
        suite=current.suite,
        passed=not (
            missing_cases
            or newly_failed
            or regressions
        ),
        new_cases=new_cases,
        missing_cases=missing_cases,
        newly_failed_cases=newly_failed,
        score_regressions=regressions,
    )