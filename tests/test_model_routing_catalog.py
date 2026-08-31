"""Phase 50: Model Routing Catalog 加载与校验测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.model_routing.catalog import load_model_catalog
from app.model_routing.errors import ModelCatalogError
from tests.helpers.model_routing import (
    build_test_document,
    write_test_policy,
)


def test_valid_policy_loads(tmp_path: Path):
    policy_path = write_test_policy(tmp_path)
    catalog = load_model_catalog(
        policy_path,
        allowed_root=tmp_path,
        substitutions={
            "$OPENAI_MODEL": "legacy-model",
            "$OPENAI_ECONOMY_MODEL": "economy-model",
            "$OPENAI_STRONG_MODEL": "strong-model",
            "$EMBEDDING_MODEL": "embedding-model",
        },
    )
    assert catalog.document.policy_version == "test-v1"
    assert len(catalog.document.profiles) == 4
    assert len(catalog.document.routes) == 13
    assert len(catalog.policy_sha256) == 64


def test_policy_sha256_stable(tmp_path: Path):
    policy_path = write_test_policy(tmp_path)
    subs = {
        "$OPENAI_MODEL": "legacy-model",
        "$OPENAI_ECONOMY_MODEL": "economy-model",
        "$OPENAI_STRONG_MODEL": "strong-model",
        "$EMBEDDING_MODEL": "embedding-model",
    }
    c1 = load_model_catalog(policy_path, allowed_root=tmp_path, substitutions=subs)
    c2 = load_model_catalog(policy_path, allowed_root=tmp_path, substitutions=subs)
    assert c1.policy_sha256 == c2.policy_sha256


def test_duplicate_profile_id_rejected(tmp_path: Path):
    doc = build_test_document()
    doc.profiles[1].profile_id = doc.profiles[0].profile_id
    policy_path = write_test_policy(tmp_path, doc)
    with pytest.raises(ModelCatalogError, match="重复 profile_id"):
        load_model_catalog(
            policy_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_duplicate_task_route_rejected(tmp_path: Path):
    doc = build_test_document()
    doc.routes[1].task_kind = doc.routes[0].task_kind
    policy_path = write_test_policy(tmp_path, doc)
    with pytest.raises(ModelCatalogError, match="重复 task route"):
        load_model_catalog(
            policy_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_unknown_profile_reference_rejected(tmp_path: Path):
    doc = build_test_document()
    doc.routes[0].candidate_profile_ids = ["nonexistent_profile"]
    policy_path = write_test_policy(tmp_path, doc)
    with pytest.raises(ModelCatalogError, match="未知 profile"):
        load_model_catalog(
            policy_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_policy_symlink_rejected(tmp_path: Path):
    policy_path = write_test_policy(tmp_path)
    link_path = tmp_path / "link.json"
    link_path.symlink_to(policy_path)
    with pytest.raises(ModelCatalogError, match="symlink"):
        load_model_catalog(
            link_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_policy_outside_allowed_root_rejected(tmp_path: Path):
    policy_path = write_test_policy(tmp_path)
    other_root = tmp_path / "other_root"
    other_root.mkdir()
    with pytest.raises(ModelCatalogError, match="ALLOWED_ROOT"):
        load_model_catalog(
            policy_path,
            allowed_root=other_root,
            substitutions={},
        )


def test_policy_not_found_rejected(tmp_path: Path):
    with pytest.raises(ModelCatalogError):
        load_model_catalog(
            tmp_path / "nonexistent.json",
            allowed_root=tmp_path,
            substitutions={},
        )


def test_oversized_policy_rejected(tmp_path: Path):
    doc = build_test_document()
    policy_path = write_test_policy(tmp_path, doc)
    # 写一个超大文件
    large_path = tmp_path / "large.json"
    large_data = json.loads(policy_path.read_text())
    large_data["_padding"] = "x" * 1_100_000
    large_path.write_text(json.dumps(large_data))
    with pytest.raises(ModelCatalogError, match="过大"):
        load_model_catalog(
            large_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_placeholder_substitution(tmp_path: Path):
    doc = build_test_document()
    policy_path = write_test_policy(tmp_path, doc)
    catalog = load_model_catalog(
        policy_path,
        allowed_root=tmp_path,
        substitutions={
            "$OPENAI_MODEL": "real-model",
            "$OPENAI_ECONOMY_MODEL": "economy-model",
            "$OPENAI_STRONG_MODEL": "strong-model",
            "$EMBEDDING_MODEL": "embedding-model",
        },
    )
    legacy = catalog.profile("legacy_chat")
    assert legacy.model_name == "real-model"


def test_unknown_placeholder_rejected(tmp_path: Path):
    doc = build_test_document()
    policy_path = write_test_policy(tmp_path, doc)
    with pytest.raises(ModelCatalogError, match="占位符"):
        load_model_catalog(
            policy_path,
            allowed_root=tmp_path,
            substitutions={
                "$OPENAI_MODEL": "real-model",
                "$OPENAI_ECONOMY_MODEL": "economy-model",
                "$OPENAI_STRONG_MODEL": "strong-model",
                # missing $EMBEDDING_MODEL
            },
        )


def test_substitution_changes_policy_sha256(tmp_path: Path):
    doc = build_test_document()
    policy_path = write_test_policy(tmp_path, doc)
    c1 = load_model_catalog(
        policy_path,
        allowed_root=tmp_path,
        substitutions={
            "$OPENAI_MODEL": "model-a",
            "$OPENAI_ECONOMY_MODEL": "economy-model",
            "$OPENAI_STRONG_MODEL": "strong-model",
            "$EMBEDDING_MODEL": "embedding-model",
        },
    )
    c2 = load_model_catalog(
        policy_path,
        allowed_root=tmp_path,
        substitutions={
            "$OPENAI_MODEL": "model-b",
            "$OPENAI_ECONOMY_MODEL": "economy-model",
            "$OPENAI_STRONG_MODEL": "strong-model",
            "$EMBEDDING_MODEL": "embedding-model",
        },
    )
    assert c1.policy_sha256 != c2.policy_sha256


def test_route_workload_mismatch_rejected(tmp_path: Path):
    doc = build_test_document()
    # 强制把 chat route 指向 embedding profile
    doc.routes[0].candidate_profile_ids = ["legacy_embedding"]
    policy_path = write_test_policy(tmp_path, doc)
    with pytest.raises(ModelCatalogError, match="workload"):
        load_model_catalog(
            policy_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_route_max_output_exceeds_profile_rejected(tmp_path: Path):
    doc = build_test_document()
    doc.routes[0].max_output_tokens = 999999
    policy_path = write_test_policy(tmp_path, doc)
    with pytest.raises(ModelCatalogError, match="max_output_tokens"):
        load_model_catalog(
            policy_path,
            allowed_root=tmp_path,
            substitutions={},
        )


def test_profile_method(tmp_path: Path):
    catalog = build_test_catalog_helper(tmp_path)
    profile = catalog.profile("legacy_chat")
    assert profile.profile_id == "legacy_chat"

    with pytest.raises(ModelCatalogError):
        catalog.profile("nonexistent")


def test_route_method(tmp_path: Path):
    catalog = build_test_catalog_helper(tmp_path)
    route = catalog.route("chat_answer")
    assert route.task_kind == "chat_answer"

    with pytest.raises(ModelCatalogError):
        catalog.route("nonexistent_task")


def build_test_catalog_helper(tmp_path: Path):
    from tests.helpers.model_routing import build_test_catalog

    return build_test_catalog(tmp_path)
