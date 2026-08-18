from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.config import settings
from app.evaluation import run_eval
from app.evaluation.baseline import write_baseline
from app.evaluation.runners import run_live_graph_case
from app.evaluation.schemas import (
    BaselineCase,
    EvalBaseline,
    EvalCase,
)


def _provider_case(
    *,
    scripted_responses: list | None = None,
) -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "provider_safety",
            "description": "provider safety",
            "suite": "provider",
            "runner": "live_graph",
            "categories": ["quality"],
            "input": {
                "paper_path": "paper.pdf",
                "repo_path": "/tmp/repo",
                "scripted_responses": scripted_responses or [],
            },
            "expected": {
                "required_files": ["train-msr.py"],
            },
        }
    )


def _failing_case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "failing_case",
            "description": "runner fails",
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
        }
    )


def test_provider_runner_rejects_scripted_responses() -> None:
    case = _provider_case(
        scripted_responses=[{"decision": "approved"}],
    )

    with pytest.raises(
        ValueError,
        match="暂不接受 scripted_responses",
    ):
        run_live_graph_case(case)


def test_single_case_filters_full_suite_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")
    baseline_path = tmp_path / "offline.json"
    write_baseline(
        EvalBaseline(
            suite="offline",
            cases=[
                BaselineCase(
                    case_id="route_executor_failure_to_debug",
                    passed=True,
                    overall_score=1.0,
                    category_scores={"route": 1.0},
                ),
                BaselineCase(
                    case_id="unselected_case",
                    passed=True,
                    overall_score=1.0,
                ),
            ],
        ),
        baseline_path,
    )

    _, result, diff = run_eval.execute_suite(
        suite="offline",
        selected_case_ids={
            "route_executor_failure_to_debug",
        },
        baseline_path=baseline_path,
        update_baseline=False,
    )

    assert result.passed is True
    assert diff is not None
    assert diff.passed is True
    assert diff.missing_cases == []


def test_failed_suite_is_not_written_as_baseline_and_error_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")
    monkeypatch.setattr(
        run_eval,
        "load_cases",
        lambda **_: [_failing_case()],
    )

    def fail_runner(_case: EvalCase):
        raise RuntimeError(
            "OPENAI_API_KEY=super-secret-value"
        )

    monkeypatch.setattr(run_eval, "run_case", fail_runner)
    baseline_path = tmp_path / "failed-baseline.json"

    _, result, _ = run_eval.execute_suite(
        suite="offline",
        selected_case_ids={"failing_case"},
        baseline_path=baseline_path,
        update_baseline=True,
    )

    assert result.passed is False
    assert not baseline_path.exists()
    assert result.case_results[0].error is not None
    assert "super-secret-value" not in result.case_results[0].error
    assert "OPENAI_API_KEY=<redacted>" in result.case_results[0].error


def test_cli_rejects_partial_baseline_update() -> None:
    result = CliRunner().invoke(
        run_eval.app,
        [
            "run",
            "--suite",
            "offline",
            "--case-id",
            "route_executor_failure_to_debug",
            "--update-baseline",
        ],
    )

    assert result.exit_code != 0
    normalized_output = " ".join(result.output.split())
    assert "--update-baseline 只能用于完整 suite" in normalized_output
    assert "不能与 --case-id" in normalized_output


def test_cli_rejects_baseline_update_outside_baseline_root(
    tmp_path: Path,
) -> None:
    result = CliRunner().invoke(
        run_eval.app,
        [
            "run",
            "--suite",
            "offline",
            "--baseline",
            str(tmp_path / "outside.json"),
            "--update-baseline",
        ],
    )

    assert result.exit_code != 0
    assert "路径必须位于" in result.output
