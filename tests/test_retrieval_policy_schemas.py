from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.retrieval.policy import (
    load_retrieval_policy,
    profile_by_id,
    sha256_value,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "config" / "retrieval_policy.json"


def test_default_policy_loads_and_has_offline_fallback():
    policy = load_retrieval_policy(POLICY_PATH)
    fallback = profile_by_id(policy, policy.fallback_profile_id)

    assert fallback.requires_dense is False
    assert "dense" not in fallback.enabled_channels
    assert len(sha256_value(policy)) == 64


def test_policy_rejects_import_graph_without_symbol(tmp_path: Path):
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    payload["profiles"][0]["enabled_channels"] = ["import_graph"]
    payload["profiles"][0]["channel_weights"] = {
        "import_graph": 1.0,
    }
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="依赖 symbol"):
        load_retrieval_policy(path)


def test_policy_hash_changes_when_weight_changes():
    policy = load_retrieval_policy(POLICY_PATH)
    changed = policy.model_copy(deep=True)
    changed.profiles[0].channel_weights["keyword"] += 0.1

    assert sha256_value(policy) != sha256_value(changed)
