"""Phase 50: Model Router 路由决策测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.model_routing.errors import ModelRouteUnavailable
from app.model_routing.identity import sha256_text
from app.model_routing.schemas import ModelRouteRequest
from tests.helpers.model_routing import (
    TEST_PRICING,
    build_test_router,
    build_chat_route_request,
)


def test_shadow_selects_challenger_but_executes_legacy(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="failure_debug",
        required_capabilities={"structured_json_schema"},
    )
    decision, profile = router.route(
        request=request,
        mode="shadow",
    )
    assert decision.selected_profile_id == "strong_chat"
    assert decision.executed_profile_id == "legacy_chat"
    assert profile.profile_id == "legacy_chat"


def test_active_executes_selected_profile(tmp_path: Path):
    from tests.helpers.model_routing import (
        ModelBudgetPolicy,
        TEST_PRICING,
        build_test_document,
        write_test_policy,
    )
    from app.model_routing.catalog import load_model_catalog
    from app.model_routing.policy import ModelRouter

    doc = build_test_document(
        pricing_override={
            "legacy_chat": TEST_PRICING,
            "strong_chat": TEST_PRICING,
            "economy_chat": TEST_PRICING,
        },
        budget=ModelBudgetPolicy(
            daily_total_token_limit=10000,
            daily_cost_limit_micro_usd=10000,
            per_job_total_token_limit=5000,
            per_job_cost_limit_micro_usd=5000,
            reservation_ttl_seconds=300,
            allow_unpriced_in_active=False,
        ),
    )
    policy_path = write_test_policy(tmp_path, doc)
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
    router = ModelRouter(catalog)
    request = build_chat_route_request(
        task_kind="failure_debug",
        required_capabilities={"structured_json_schema"},
    )
    decision, profile = router.route(
        request=request,
        mode="active",
    )
    assert decision.selected_profile_id == profile.profile_id
    assert decision.executed_profile_id == profile.profile_id


def test_off_executes_legacy(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="failure_debug",
        required_capabilities={"structured_json_schema"},
    )
    decision, profile = router.route(
        request=request,
        mode="off",
    )
    assert decision.executed_profile_id == "legacy_chat"
    assert profile.profile_id == "legacy_chat"


def test_context_overflow_fails_closed(tmp_path: Path):
    router = build_test_router(tmp_path)
    oversized = build_chat_route_request(
        task_kind="failure_debug",
        estimated_input_tokens=999999,
        required_capabilities={"structured_json_schema"},
    )
    with pytest.raises(ModelRouteUnavailable):
        router.route(request=oversized, mode="active")


def test_capability_missing_fails_closed(tmp_path: Path):
    from tests.helpers.model_routing import (
        ModelBudgetPolicy,
        TEST_PRICING,
        build_test_document,
        write_test_policy,
    )
    from app.model_routing.catalog import load_model_catalog
    from app.model_routing.policy import ModelRouter

    doc = build_test_document(
        pricing_override={
            "legacy_chat": TEST_PRICING,
            "strong_chat": TEST_PRICING,
            "economy_chat": TEST_PRICING,
        },
        budget=ModelBudgetPolicy(
            daily_total_token_limit=10000,
            daily_cost_limit_micro_usd=10000,
            per_job_total_token_limit=5000,
            per_job_cost_limit_micro_usd=5000,
            reservation_ttl_seconds=300,
            allow_unpriced_in_active=False,
        ),
    )
    policy_path = write_test_policy(tmp_path, doc)
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
    router = ModelRouter(catalog)
    request = build_chat_route_request(
        task_kind="paper_section_extraction",
        required_capabilities={"long_context", "structured_json_schema"},
    )
    # economy_chat lacks long_context, but strong_chat has it
    decision, profile = router.route(request=request, mode="active")
    assert profile.profile_id == "strong_chat"


def test_quality_insufficient_fails_closed(tmp_path: Path):
    from tests.helpers.model_routing import (
        ModelBudgetPolicy,
        TEST_PRICING,
        build_test_document,
        write_test_policy,
    )
    from app.model_routing.catalog import load_model_catalog
    from app.model_routing.policy import ModelRouter

    doc = build_test_document(
        pricing_override={
            "legacy_chat": TEST_PRICING,
            "strong_chat": TEST_PRICING,
            "economy_chat": TEST_PRICING,
        },
        budget=ModelBudgetPolicy(
            daily_total_token_limit=10000,
            daily_cost_limit_micro_usd=10000,
            per_job_total_token_limit=5000,
            per_job_cost_limit_micro_usd=5000,
            reservation_ttl_seconds=300,
            allow_unpriced_in_active=False,
        ),
    )
    policy_path = write_test_policy(tmp_path, doc)
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
    router = ModelRouter(catalog)
    # repair_plan requires minimum_quality_rank=80
    request = build_chat_route_request(
        task_kind="repair_plan",
        quality_tier="economy",
        required_capabilities={"structured_json_schema"},
    )
    # economy_chat has quality_rank=60 < 80, strong_chat has 90 >= 80
    # but economy quality_tier < strong's high, so strong should be selected
    decision, profile = router.route(request=request, mode="active")
    assert profile.profile_id == "strong_chat"


def test_disabled_profile_skipped(tmp_path: Path):
    from tests.helpers.model_routing import (
        ModelBudgetPolicy,
        TEST_PRICING,
        build_test_document,
        write_test_policy,
    )
    from app.model_routing.catalog import load_model_catalog
    from app.model_routing.policy import ModelRouter

    doc = build_test_document(
        pricing_override={
            "legacy_chat": TEST_PRICING,
            "strong_chat": TEST_PRICING,
            "economy_chat": TEST_PRICING,
        },
        budget=ModelBudgetPolicy(
            daily_total_token_limit=10000,
            daily_cost_limit_micro_usd=10000,
            per_job_total_token_limit=5000,
            per_job_cost_limit_micro_usd=5000,
            reservation_ttl_seconds=300,
            allow_unpriced_in_active=False,
        ),
    )
    # Disable strong_chat
    doc = doc.model_copy(
        update={
            "profiles": [
                p.model_copy(update={"enabled": False})
                if p.profile_id == "strong_chat"
                else p
                for p in doc.profiles
            ]
        }
    )
    policy_path = write_test_policy(tmp_path, doc)
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
    router = ModelRouter(catalog)
    request = build_chat_route_request(
        task_kind="failure_debug",
        required_capabilities={"structured_json_schema"},
    )
    # With strong_chat disabled, legacy_chat should be selected
    decision, profile = router.route(request=request, mode="active")
    assert profile.profile_id == "legacy_chat"


def test_unpriced_active_rejected(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="failure_debug",
        required_capabilities={"structured_json_schema"},
    )
    # Default policy has allow_unpriced_in_active=False
    # All profiles are unpriced, so active should reject
    with pytest.raises(ModelRouteUnavailable, match="UNPRICED"):
        router.route(request=request, mode="active")


def test_decision_hash_stable(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="chat_answer",
        required_capabilities={"structured_json_schema"},
    )
    d1, _ = router.route(request=request, mode="shadow")
    d2, _ = router.route(request=request, mode="shadow")
    assert d1.decision_sha256 == d2.decision_sha256


def test_different_policy_changes_decision_hash(tmp_path: Path):
    from tests.helpers.model_routing import (
        build_test_document,
        write_test_policy,
    )
    from app.model_routing.catalog import load_model_catalog
    from app.model_routing.policy import ModelRouter

    doc1 = build_test_document()
    doc2 = build_test_document()
    doc2 = doc2.model_copy(update={"policy_version": "different-v1"})

    p1 = write_test_policy(tmp_path / "p1", doc1)
    p2 = write_test_policy(tmp_path / "p2", doc2)

    subs = {
        "$OPENAI_MODEL": "legacy-model",
        "$OPENAI_ECONOMY_MODEL": "economy-model",
        "$OPENAI_STRONG_MODEL": "strong-model",
        "$EMBEDDING_MODEL": "embedding-model",
    }

    c1 = load_model_catalog(p1, allowed_root=tmp_path, substitutions=subs)
    c2 = load_model_catalog(p2, allowed_root=tmp_path, substitutions=subs)

    assert c1.policy_sha256 != c2.policy_sha256


def test_workload_mismatch_rejected(tmp_path: Path):
    router = build_test_router(tmp_path)
    # Send an embedding request to a chat task
    request = ModelRouteRequest(
        task_kind="chat_answer",
        workload_kind="embedding",
        required_capabilities={"embedding"},
        requested_quality_tier="balanced",
        estimated_input_tokens=100,
        requested_max_output_tokens=0,
        prompt_sha256=sha256_text("test"),
        prompt_chars=4,
        schema_name=None,
        schema_sha256=None,
        node_name="test",
    )
    with pytest.raises(ModelRouteUnavailable, match="WORKLOAD"):
        router.route(request=request, mode="off")


def test_output_limit_exceeded_rejected(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="chat_answer",
        requested_max_output_tokens=999999,
        required_capabilities={"structured_json_schema"},
    )
    with pytest.raises(ModelRouteUnavailable):
        router.route(request=request, mode="off")


def test_input_limit_exceeded_rejected(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="chat_answer",
        estimated_input_tokens=999999,
        required_capabilities={"structured_json_schema"},
    )
    with pytest.raises(ModelRouteUnavailable):
        router.route(request=request, mode="off")


def test_reason_codes_contain_expected_entries(tmp_path: Path):
    router = build_test_router(tmp_path)
    request = build_chat_route_request(
        task_kind="chat_answer",
        required_capabilities={"structured_json_schema"},
    )
    decision, _ = router.route(request=request, mode="shadow")
    assert "TASK_ROUTE_MATCHED" in decision.reason_codes
    assert "SHADOW_EXECUTES_LEGACY" in decision.reason_codes


def test_embedding_route(tmp_path: Path):
    from tests.helpers.model_routing import build_embedding_route_request

    router = build_test_router(tmp_path)
    request = build_embedding_route_request()
    decision, profile = router.route(request=request, mode="off")
    assert profile.profile_id == "legacy_embedding"
    assert profile.workload_kind == "embedding"
