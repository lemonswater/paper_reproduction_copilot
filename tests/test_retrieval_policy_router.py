from __future__ import annotations

from pathlib import Path

from app.retrieval.policy import (
    build_query_features,
    load_retrieval_policy,
    select_retrieval_profile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY = load_retrieval_policy(
    PROJECT_ROOT / "config" / "retrieval_policy.json"
)


def test_exact_error_routes_to_lexical_profile():
    features = build_query_features(
        query="ImportError: undefined symbol CUDART_120",
        keywords=["CUDART_120"],
    )
    decision = select_retrieval_profile(
        policy=POLICY,
        features=features,
        dense_available=True,
        mode="active",
    )

    assert features.query_kind == "exact_error"
    assert decision.selected_profile.profile_id == "exact_lexical_v1"
    assert "dense" not in decision.selected_profile.enabled_channels
    assert decision.applied is True


def test_symbol_routes_to_symbol_path_profile():
    features = build_query_features(
        query="PSTConv",
        keywords=["PSTConv"],
    )
    decision = select_retrieval_profile(
        policy=POLICY,
        features=features,
        dense_available=False,
        mode="active",
    )

    assert features.query_kind == "symbol_path"
    assert decision.selected_profile.profile_id == "symbol_path_v1"


def test_semantic_query_uses_dense_only_when_available():
    query = (
        "Locate the module that forms neighborhoods of three dimensional "
        "points over consecutive frames and jointly aggregates spatial "
        "and temporal motion features without relying on matching names."
    )
    features = build_query_features(
        query=query,
        keywords=[],
        paper_evidence_count=2,
    )

    dense = select_retrieval_profile(
        policy=POLICY,
        features=features,
        dense_available=True,
        mode="active",
    )
    sparse = select_retrieval_profile(
        policy=POLICY,
        features=features,
        dense_available=False,
        mode="active",
    )

    assert features.query_kind == "semantic_alignment"
    assert dense.selected_profile.profile_id == "semantic_hybrid_v1"
    assert sparse.selected_profile.profile_id == "balanced_sparse_v1"
    assert sparse.fallback_used is False
    assert any(
        value.startswith("RULE_SKIPPED_DENSE_UNAVAILABLE")
        for value in sparse.reason_codes
    )


def test_shadow_decision_never_applies_profile():
    features = build_query_features(
        query="PSTConv",
        keywords=["PSTConv"],
    )
    decision = select_retrieval_profile(
        policy=POLICY,
        features=features,
        dense_available=True,
        mode="shadow",
    )

    assert decision.applied is False
    assert decision.mode == "shadow"
