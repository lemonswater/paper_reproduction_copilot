from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import settings
from app.evaluation.case_loader import (
    load_case_file,
)
from app.evaluation.runners import run_case
from app.evaluation.schemas import (
    EvalCase,
    EvalMetrics,
    EvalObservation,
)
from app.evaluation.scorers import score_case

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_CASE = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "cases"
    / "provider"
    / "retrieval_obfuscated_semantics.json"
)


def test_semantic_runner_rejects_offline_suite():
    payload = {
        "case_id": "invalid_offline_dense",
        "description": "must be rejected",
        "suite": "offline",
        "runner": "semantic_code_retrieval",
        "categories": ["evidence"],
        "input": {
            "repo_path": (
                "fixtures/retrieval_repo"
            ),
            "retrieval_query": (
                "semantic behavior"
            ),
        },
        "expected": {},
    }

    with pytest.raises(
        ValueError,
        match="provider suite",
    ):
        EvalCase.model_validate(payload)


def test_efficiency_scorer_checks_embedding_budget():
    case = EvalCase.model_validate(
        {
            "case_id": "embedding_budget",
            "description": "embedding budget",
            "suite": "provider",
            "runner": (
                "semantic_code_retrieval"
            ),
            "categories": ["efficiency"],
            "input": {
                "repo_path": (
                    "fixtures/retrieval_repo"
                ),
                "retrieval_query": "behavior",
            },
            "expected": {
                "max_embedding_document_calls": 2,
                "max_embedding_query_calls": 1,
            },
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner=(
            "semantic_code_retrieval"
        ),
        metrics=EvalMetrics(
            embedding_document_calls=3,
            embedding_query_calls=1,
        ),
    )

    result = score_case(
        case,
        observation,
    )

    assert result.passed is False
    assert any(
        assertion.code
        == (
            "EFFICIENCY_"
            "EMBEDDING_DOCUMENT_CALLS"
        )
        and not assertion.passed
        for scorer in result.scorer_results
        for assertion in scorer.assertions
    )


@pytest.mark.provider
def test_real_embedding_provider_case():
    if (
        not os.getenv("EMBEDDING_API_KEY")
        or not os.getenv(
            "EMBEDDING_BASE_URL"
        )
        or not settings
        .allow_code_embedding_upload
    ):
        pytest.skip(
            "真实 Embedding Provider 未显式配置"
        )

    case = load_case_file(PROVIDER_CASE)
    observation = run_case(case)
    result = score_case(
        case,
        observation,
    )

    assert result.passed, [
        assertion.model_dump()
        for scorer in result.scorer_results
        for assertion in scorer.assertions
        if not assertion.passed
    ]