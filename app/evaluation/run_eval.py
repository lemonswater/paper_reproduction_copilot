from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from app.evaluation.baseline import (
    build_baseline,
    compare_baseline,
    load_baseline,
    write_baseline,
)
from app.evaluation.case_loader import (
    DEFAULT_CASE_DIR,
    EVALUATION_ROOT,
    load_cases,
)
from app.evaluation.reporting import render_eval_report
from app.evaluation.runners import run_case
from app.evaluation.schemas import (
    BaselineDiff,
    EvalCaseResult,
    EvalSuiteResult,
)
from app.evaluation.scorers import score_case
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import sanitize_error_message

app = typer.Typer(help="Agent 回归评测")
BASELINE_DIR = EVALUATION_ROOT / "baselines"
CORE_CATEGORIES = {
    "schema", "route", "tool", "evidence",
    "safety", "recovery", "quality", "efficiency",
}

SUPPORTED_SUITES = {
    "offline",
    "provider",
    "chat_offline",
    "chat_provider",
    "decision_offline",
    "decision_provider",
}


def _git_revision() -> tuple[str | None, bool | None]:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            shell=False,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            ).stdout.strip()
        )
        return revision, dirty
    except (OSError, subprocess.SubprocessError):
        return None, None


def _suite_result(
    *,
    eval_id: str,
    suite: str,
    cases,
    results: list[EvalCaseResult],
    require_core_coverage: bool,
) -> EvalSuiteResult:
    category_values: dict[str, list[float]] = {}
    for result in results:
        for scorer in result.scorer_results:
            category_values.setdefault(
                scorer.category,
                [],
            ).append(scorer.score)

    category_scores = {
        name: sum(values) / len(values)
        for name, values in category_values.items()
    }
    problem_coverage: dict[str, list[str]] = {}
    for case in cases:
        for problem_id in case.problem_ids:
            problem_coverage.setdefault(
                str(problem_id),
                [],
            ).append(case.case_id)

    revision, dirty = _git_revision()
    coverage_ok = (
        set(category_scores) >= CORE_CATEGORIES
        if suite == "offline" and require_core_coverage
        else True
    )
    score = (
        sum(item.overall_score for item in results) / len(results)
        if results
        else 0.0
    )
    return EvalSuiteResult(
        eval_id=eval_id,
        suite=suite,
        passed=(
            bool(results)
            and all(item.passed for item in results)
            and coverage_ok
        ),
        overall_score=score,
        case_results=results,
        category_scores=category_scores,
        problem_coverage=problem_coverage,
        generated_at=datetime.now(timezone.utc).isoformat(),
        revision=revision,
        dirty_worktree=dirty,
    )


def execute_suite(
    *,
    suite: str,
    selected_case_ids: set[str] | None,
    baseline_path: Path,
    update_baseline: bool,
) -> tuple[dict, EvalSuiteResult, BaselineDiff | None]:
    eval_id = f"agent-eval-{suite}-{uuid4().hex[:10]}"
    state = {
        "task_id": eval_id,
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
    }
    state.update(run_context_node(state))

    cases = load_cases(
        case_dir=DEFAULT_CASE_DIR,
        suite=suite,
        case_ids=selected_case_ids,
    )
    results: list[EvalCaseResult] = []

    for case in cases:
        try:
            case_work_dir = (
                Path(state["run_dir"])
                / "traces"
                / "eval_cases"
                / case.case_id
            )
            case_work_dir.mkdir(parents=True, exist_ok=True)
            observation = run_case(
                case,
                work_dir=case_work_dir,
            )
            path, record = write_json_artifact(
                state=state,
                relative_path=(
                    f"traces/eval_cases/{case.case_id}/"
                    "observation.json"
                ),
                payload=observation.model_dump(),
                producer_node="agent_eval",
            )
            state.update(artifact_state_update(state, [record]))
            results.append(
                score_case(
                    case,
                    observation,
                    observation_path=str(path),
                )
            )
        except Exception as exc:  # noqa: BLE001
            # Case 隔离边界：单个坏 fixture 不能阻止其余回归执行。
            results.append(
                EvalCaseResult(
                    case_id=case.case_id,
                    suite=case.suite,
                    runner=case.runner,
                    passed=False,
                    overall_score=0.0,
                    error=sanitize_error_message(
                        f"{type(exc).__name__}: {exc}"
                    ),
                )
            )

    result = _suite_result(
        eval_id=eval_id,
        suite=suite,
        cases=cases,
        results=results,
        require_core_coverage=selected_case_ids is None,
    )
    baseline = load_baseline(baseline_path)
    if baseline is not None and selected_case_ids:
        baseline = baseline.model_copy(
            update={
                "cases": [
                    item
                    for item in baseline.cases
                    if item.case_id in selected_case_ids
                ]
            }
        )
    diff = (
        compare_baseline(
            baseline=baseline,
            current=result,
            cases_by_id={item.case_id: item for item in cases},
        )
        if baseline is not None
        else None
    )

    _, report_record = write_json_artifact(
        state=state,
        relative_path="reports/eval_suite.json",
        payload=result.model_dump(),
        producer_node="agent_eval",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="reports/eval_report.md",
        text=render_eval_report(result, diff),
        producer_node="agent_eval",
        media_type="text/markdown",
    )
    records = [report_record, md_record]
    if diff is not None:
        _, diff_record = write_json_artifact(
            state=state,
            relative_path="reports/baseline_diff.json",
            payload=diff.model_dump(),
            producer_node="agent_eval",
        )
        records.append(diff_record)
    state.update(artifact_state_update(state, records))

    if update_baseline and result.passed:
        write_baseline(build_baseline(result), baseline_path)

    state["final_status"] = (
        "succeeded"
        if result.passed and (diff is None or diff.passed)
        else "failed"
    )
    state.update(run_manifest_node(state))
    return state, result, diff


@app.callback()
def main() -> None:
    """保留 Typer 命令组，使教程中的 `run` 始终是显式子命令。"""


@app.command("run")
def run(
    suite: Annotated[
        str,
        typer.Option("--suite"),
    ] = "offline",
    case_id: Annotated[
        list[str] | None,
        typer.Option("--case-id"),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option("--baseline"),
    ] = None,
    update_baseline: Annotated[
        bool,
        typer.Option("--update-baseline"),
    ] = False,
    fail_on_regression: Annotated[
        bool,
        typer.Option(
            "--fail-on-regression/--no-fail-on-regression"
        ),
    ] = True,
) -> None:
    if suite not in SUPPORTED_SUITES:
        raise typer.BadParameter(
            "suite 必须是：" + ", ".join(sorted(SUPPORTED_SUITES))
        )

    if update_baseline and case_id:
        raise typer.BadParameter(
            "--update-baseline 只能用于完整 suite，"
            "不能与 --case-id 同时使用"
        )

    baseline_path = (
        baseline or BASELINE_DIR / f"{suite}.json"
    ).resolve()
    baseline_root = BASELINE_DIR.resolve()
    if update_baseline and baseline_root not in baseline_path.parents:
        raise typer.BadParameter(
            "更新 baseline 时，路径必须位于 "
            f"{baseline_root}"
        )

    state, result, diff = execute_suite(
        suite=suite,
        selected_case_ids=set(case_id or []) or None,
        baseline_path=baseline_path,
        update_baseline=update_baseline,
    )
    typer.echo(
        {
            "eval_id": result.eval_id,
            "run_dir": state["run_dir"],
            "passed": result.passed,
            "score": result.overall_score,
            "baseline_diff_passed": diff.passed if diff else None,
        }
    )

    failed = not result.passed or (diff is not None and not diff.passed)
    if fail_on_regression and failed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()