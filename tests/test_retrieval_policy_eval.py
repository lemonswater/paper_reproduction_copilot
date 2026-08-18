from __future__ import annotations

from pathlib import Path

from app.retrieval.policy import load_retrieval_policy
from app.retrieval.policy_eval import (
    load_policy_cases,
    run_policy_eval,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_policy_eval_is_offline_and_produces_proposals():
    policy = load_retrieval_policy(
        PROJECT_ROOT / "config" / "retrieval_policy.json"
    )
    cases = load_policy_cases(
        PROJECT_ROOT
        / "app"
        / "evaluation"
        / "retrieval_policy_cases"
    )

    report = run_policy_eval(policy=policy, cases=cases)

    assert report.case_metrics
    assert report.promotion_proposals
    assert all(
        item.citation_coverage == 1.0
        for item in report.case_metrics
        if item.passed_hard_gate
    )
    assert all(
        item.provenance_ratio == 1.0
        for item in report.case_metrics
        if item.observed_paths
    )
    assert all(
        item.forbidden_path_count == 0
        for item in report.case_metrics
        if item.passed_hard_gate
    )


def test_semantic_challenger_never_loses_to_sparse_baseline():
    policy = load_retrieval_policy(
        PROJECT_ROOT / "config" / "retrieval_policy.json"
    )
    cases = load_policy_cases(
        PROJECT_ROOT
        / "app"
        / "evaluation"
        / "retrieval_policy_cases"
    )
    report = run_policy_eval(policy=policy, cases=cases)

    values = {
        (item.case_id, item.profile_id): item
        for item in report.case_metrics
    }
    baseline = values[
        ("phase47_semantic_gap", "balanced_sparse_v1")
    ]
    challenger = values[
        ("phase47_semantic_gap", "semantic_hybrid_v1")
    ]

    assert challenger.recall_at_k >= baseline.recall_at_k
    assert (
        challenger.mean_reciprocal_rank
        >= baseline.mean_reciprocal_rank
    )
    assert challenger.passed_hard_gate is True
