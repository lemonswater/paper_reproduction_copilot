"""Phase 50: Model Routing Evaluation 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.model_routing.evaluation import (
    build_promotion_proposal,
    evaluate_routing_cases,
)
from app.model_routing.schemas import (
    ModelProfilePromotionProposal,
    ModelRoutingEvaluationCase,
    ModelRoutingEvaluationReport,
)
from tests.helpers.model_routing import (
    ModelBudgetPolicy,
    TEST_PRICING,
    build_chat_route_request,
    build_test_document,
    build_test_router,
    write_test_policy,
)
from app.model_routing.catalog import load_model_catalog
from app.model_routing.policy import ModelRouter


def _build_priced_router(tmp_path: Path) -> ModelRouter:
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
    return ModelRouter(catalog)


def test_all_cases_pass(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    cases = [
        ModelRoutingEvaluationCase(
            case_id="case_001",
            request=build_chat_route_request(
                task_kind="failure_debug",
                required_capabilities={"structured_json_schema"},
            ),
            expected_profile_id="strong_chat",
            forbidden_profile_ids=[],
        ),
        ModelRoutingEvaluationCase(
            case_id="case_002",
            request=build_chat_route_request(
                task_kind="chat_answer",
                required_capabilities={"structured_json_schema"},
            ),
            expected_profile_id="legacy_chat",
            forbidden_profile_ids=[],
        ),
    ]
    report = evaluate_routing_cases(
        router=router,
        cases=cases,
        suite_version="phase50-routing-v1",
        mode="active",
    )
    assert report.passed is True
    assert report.total_cases == 2
    assert report.passed_cases == 2
    assert report.route_accuracy == 1.0
    assert report.failed_case_ids == []


def test_case_fails_wrong_expected(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    cases = [
        ModelRoutingEvaluationCase(
            case_id="case_wrong",
            request=build_chat_route_request(
                task_kind="failure_debug",
                required_capabilities={"structured_json_schema"},
            ),
            expected_profile_id="economy_chat",  # Wrong: should be strong_chat
            forbidden_profile_ids=[],
        ),
    ]
    report = evaluate_routing_cases(
        router=router,
        cases=cases,
        suite_version="phase50-routing-v1",
        mode="active",
    )
    assert report.passed is False
    assert "case_wrong" in report.failed_case_ids


def test_case_fails_forbidden_profile(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    cases = [
        ModelRoutingEvaluationCase(
            case_id="case_forbidden",
            request=build_chat_route_request(
                task_kind="failure_debug",
                required_capabilities={"structured_json_schema"},
            ),
            expected_profile_id="strong_chat",
            forbidden_profile_ids=["strong_chat"],  # Contradicts expected
        ),
    ]
    report = evaluate_routing_cases(
        router=router,
        cases=cases,
        suite_version="phase50-routing-v1",
        mode="active",
    )
    assert report.passed is False
    assert "case_forbidden" in report.failed_case_ids


def test_empty_cases_report(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    report = evaluate_routing_cases(
        router=router,
        cases=[],
        suite_version="phase50-routing-v1",
        mode="active",
    )
    assert report.total_cases == 0
    assert report.passed is False  # empty suite doesn't pass


def test_promotion_requires_route_and_downstream_quality(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    cases = [
        ModelRoutingEvaluationCase(
            case_id="case_001",
            request=build_chat_route_request(
                task_kind="chat_memory_compaction",
                required_capabilities={"structured_json_schema"},
            ),
            expected_profile_id="economy_chat",
            forbidden_profile_ids=[],
        ),
    ]
    report = evaluate_routing_cases(
        router=router,
        cases=cases,
        suite_version="phase50-routing-v1",
        mode="active",
    )
    proposal = build_promotion_proposal(
        task_kind="chat_memory_compaction",
        baseline_profile_id="legacy_chat",
        challenger_profile_id="economy_chat",
        baseline_policy_sha256=router.catalog.policy_sha256,
        route_report=report,
        downstream_quality_gate_passed=False,
        estimated_saving_percent=50.0,
    )
    assert proposal.quality_gate_passed is False
    assert proposal.requires_explicit_user_review is True


def test_promotion_passes_when_both_gates_pass(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    cases = [
            ModelRoutingEvaluationCase(
            case_id="case_001",
            request=build_chat_route_request(
                task_kind="chat_memory_compaction",
                required_capabilities={"structured_json_schema"},
                quality_tier="economy",
            ),
            expected_profile_id="economy_chat",
            forbidden_profile_ids=[],
        ),
    ]
    report = evaluate_routing_cases(
        router=router,
        cases=cases,
        suite_version="phase50-routing-v1",
        mode="active",
    )
    proposal = build_promotion_proposal(
        task_kind="chat_memory_compaction",
        baseline_profile_id="legacy_chat",
        challenger_profile_id="economy_chat",
        baseline_policy_sha256=router.catalog.policy_sha256,
        route_report=report,
        downstream_quality_gate_passed=True,
        estimated_saving_percent=50.0,
    )
    assert proposal.quality_gate_passed is True
    assert proposal.requires_explicit_user_review is True


def test_promotion_id_stable(tmp_path: Path):
    router = _build_priced_router(tmp_path)
    cases = [
        ModelRoutingEvaluationCase(
            case_id="case_001",
            request=build_chat_route_request(
                task_kind="chat_memory_compaction",
                required_capabilities={"structured_json_schema"},
            ),
            expected_profile_id="economy_chat",
        ),
    ]
    report = evaluate_routing_cases(
        router=router,
        cases=cases,
        suite_version="phase50-routing-v1",
        mode="active",
    )
    p1 = build_promotion_proposal(
        task_kind="chat_memory_compaction",
        baseline_profile_id="legacy_chat",
        challenger_profile_id="economy_chat",
        baseline_policy_sha256=router.catalog.policy_sha256,
        route_report=report,
        downstream_quality_gate_passed=True,
        estimated_saving_percent=50.0,
    )
    p2 = build_promotion_proposal(
        task_kind="chat_memory_compaction",
        baseline_profile_id="legacy_chat",
        challenger_profile_id="economy_chat",
        baseline_policy_sha256=router.catalog.policy_sha256,
        route_report=report,
        downstream_quality_gate_passed=True,
        estimated_saving_percent=50.0,
    )
    assert p1.proposal_id == p2.proposal_id


def test_no_real_provider_imports():
    """Evaluation 模块源码不得直接 import app.model 或 langchain_openai。"""
    import ast
    import inspect

    import app.model_routing.evaluation as eval_mod

    source = inspect.getsource(eval_mod)
    tree = ast.parse(source)

    forbidden_modules = {"app.model", "langchain_openai"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules, (
                    f"evaluation 模块禁止 import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden_modules, (
                f"evaluation 模块禁止 from-import: {node.module}"
            )
