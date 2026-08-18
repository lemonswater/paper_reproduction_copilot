from __future__ import annotations

from pathlib import Path

import pytest

from app.evaluation.case_loader import (
    load_case_file,
)
from app.evaluation.runners import run_case
from app.evaluation.schemas import EvalCase
from app.evaluation.scorers import score_case

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "cases"
    / "offline"
)


@pytest.mark.parametrize(
    "case_name",
    [
        "retrieval_pstconv.json",
        "retrieval_training_config.json",
    ],
)
def test_retrieval_golden_case_passes(
    case_name,
):
    case = load_case_file(
        CASE_ROOT / case_name
    )

    observation = run_case(case)
    result = score_case(
        case,
        observation,
    )

    assert observation.metrics.llm_calls == 0
    assert observation.code_retrieval
    assert result.passed, [
        assertion.model_dump()
        for scorer in result.scorer_results
        for assertion in scorer.assertions
        if not assertion.passed
    ]


def test_code_retrieval_rejects_provider_suite():
    payload = {
        "case_id": "invalid_provider_retrieval",
        "description": "must be rejected",
        "suite": "provider",
        "runner": "code_retrieval",
        "categories": ["evidence"],
        "input": {
            "repo_path": "fixtures/retrieval_repo",
            "retrieval_query": "PSTConv",
        },
        "expected": {},
    }

    with pytest.raises(
        ValueError,
        match="必须放入 offline suite",
    ):
        EvalCase.model_validate(payload)