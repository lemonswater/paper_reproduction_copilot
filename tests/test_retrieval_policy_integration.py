from __future__ import annotations

from pathlib import Path

import pytest

from app.retrieval.indexer import build_repository_index
from app.retrieval.policy import (
    load_retrieval_policy,
    profile_by_id,
)
from app.retrieval.service import (
    build_evidence_pack,
    validate_code_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "fixtures"
    / "retrieval_repo"
)


def test_profile_limits_observed_channels_without_weakening_evidence():
    policy = load_retrieval_policy(
        PROJECT_ROOT / "config" / "retrieval_policy.json"
    )
    profile = profile_by_id(policy, "symbol_path_v1")
    index = build_repository_index(
        REPO_ROOT,
        index_version="phase47-test-v1",
    )

    _, pack = build_evidence_pack(
        repo_path=REPO_ROOT,
        query="PSTConv",
        keywords=["PSTConv"],
        index=index,
        enabled_channels=profile.enabled_channels,
        channel_weights=profile.channel_weights,
        top_k=profile.top_k,
        rrf_k=profile.rrf_k,
    )

    assert pack.items
    allowed = set(profile.enabled_channels)
    assert all(
        set(item.retrieval_channels) <= allowed
        for item in pack.items
    )
    assert all(
        validate_code_evidence(
            repo_path=REPO_ROOT,
            evidence=item,
        )
        for item in pack.items
    )


def test_import_graph_without_symbol_fails_closed():
    index = build_repository_index(
        REPO_ROOT,
        index_version="phase47-test-v1",
    )

    with pytest.raises(ValueError, match="依赖 symbol"):
        build_evidence_pack(
            repo_path=REPO_ROOT,
            query="PSTConv",
            keywords=["PSTConv"],
            index=index,
            enabled_channels=["import_graph"],
        )
