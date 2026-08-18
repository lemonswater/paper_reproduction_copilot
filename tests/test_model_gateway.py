"""Phase 50: Model Gateway 集成测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from app.model_routing.errors import ModelBudgetExceeded
from app.model_routing.gateway import ModelGateway, RoutedStructuredInvocation
from app.model_routing.schemas import ModelInvocationRecord, ModelUsage
from app.tools.structured_output_tools import (
    StructuredInvocationResult,
    StructuredOutputAttempt,
)
from tests.helpers.model_routing import (
    FakeProviders,
    TEST_PRICING,
    ModelBudgetPolicy,
    build_test_document,
    build_test_gateway,
)


class FakeDraft(BaseModel):
    answer: str = "test"


def _make_attempt(
    *,
    status: str = "succeeded",
    token_usage: dict | None = None,
    finish_reason: str | None = "stop",
    output_chars: int = 100,
    truncated: bool = False,
) -> StructuredOutputAttempt:
    return StructuredOutputAttempt(
        attempt_number=1,
        status=status,
        prompt_kind="original",
        token_usage=token_usage,
        finish_reason=finish_reason,
        output_chars=output_chars,
        truncated=truncated,
    )


def _make_structured_result(
    *,
    succeeded: bool = True,
    attempts: list | None = None,
    value: Any = None,
) -> StructuredInvocationResult:
    if attempts is None:
        attempts = [_make_attempt()]
    return StructuredInvocationResult(
        value=(value if value is not None else (FakeDraft(answer="ok") if succeeded else None)),
        attempts=attempts,
        method="json_schema",
        strict=True,
        max_retries=0,
        provider_max_retries=0,
        provider_retry_base_seconds=0,
    )


def _make_fake_invoker(result: StructuredInvocationResult):
    def invoker(**kwargs):
        return result
    return invoker


def _build_priced_gateway(
    tmp_path: Path,
    *,
    mode: str = "active",
    chat: Any = None,
    structured_invoker=None,
) -> ModelGateway:
    doc = build_test_document(
        pricing_override={
            "legacy_chat": TEST_PRICING,
            "strong_chat": TEST_PRICING,
            "economy_chat": TEST_PRICING,
        },
        budget=ModelBudgetPolicy(
            daily_total_token_limit=100000,
            daily_cost_limit_micro_usd=100000,
            per_job_total_token_limit=50000,
            per_job_cost_limit_micro_usd=50000,
            reservation_ttl_seconds=300,
            allow_unpriced_in_active=False,
        ),
    )
    providers = FakeProviders(chat=chat or object())
    return build_test_gateway(
        tmp_path,
        mode=mode,
        providers=providers,
        structured_invoker=structured_invoker,
        document=doc,
    )


def test_off_mode_does_not_write_ledger(tmp_path: Path):
    result = _make_structured_result()
    gateway = _build_priced_gateway(
        tmp_path,
        mode="off",
        structured_invoker=_make_fake_invoker(result),
    )
    invocation = gateway.invoke_structured(
        task_kind="chat_answer",
        schema=FakeDraft,
        prompt="test prompt",
        node_name="test_node",
    )
    assert invocation.ledger_record is None
    assert invocation.invocation_id is None


def test_shadow_executes_legacy_profile(tmp_path: Path):
    result = _make_structured_result()
    gateway = _build_priced_gateway(
        tmp_path,
        mode="shadow",
        structured_invoker=_make_fake_invoker(result),
    )
    invocation = gateway.invoke_structured(
        task_kind="chat_answer",
        schema=FakeDraft,
        prompt="test prompt",
        node_name="test_node",
    )
    assert invocation.decision.executed_profile_id == "legacy_chat"
    assert invocation.ledger_record is not None


def test_active_executes_selected_profile(tmp_path: Path):
    result = _make_structured_result()
    gateway = _build_priced_gateway(
        tmp_path,
        mode="active",
        structured_invoker=_make_fake_invoker(result),
    )
    invocation = gateway.invoke_structured(
        task_kind="failure_debug",
        schema=FakeDraft,
        prompt="test prompt",
        node_name="test_node",
    )
    assert invocation.decision.executed_profile_id == "strong_chat"
    assert invocation.ledger_record is not None


def test_preview_does_not_build_provider(tmp_path: Path):
    providers = FakeProviders()
    doc = build_test_document(
        pricing_override={
            "legacy_chat": TEST_PRICING,
            "strong_chat": TEST_PRICING,
        },
    )
    gateway = build_test_gateway(
        tmp_path,
        mode="active",
        providers=providers,
        document=doc,
    )
    decision = gateway.preview_structured(
        task_kind="chat_answer",
        schema=FakeDraft,
        prompt="preview test",
        node_name="preview_node",
    )
    assert providers.chat_builds == 0
    assert decision.selected_profile_id is not None


def test_budget_denied_does_not_build_provider(tmp_path: Path):
    result = _make_structured_result()
    gateway = _build_priced_gateway(
        tmp_path,
        mode="active",
        structured_invoker=_make_fake_invoker(result),
    )
    # Fill budget: 66 * 1500 = 99000, leaving only 1000 remaining
    for i in range(66):
        from tests.helpers.model_routing import TEST_BUDGET
        from app.model_routing.repository import SqliteModelLedger
        from app.model_routing.schemas import ModelReservationRequest
        from datetime import timedelta

        from app.model_routing.repository import iso_utc, utc_now

        r = ModelReservationRequest(
            invocation_id=f"mdl_{i:032x}",
            request_sha256="0" * 64,
            decision_sha256="0" * 64,
            task_kind="chat_answer",
            job_id=None,
            run_id=None,
            node_name="fill_budget",
            profile_id="legacy_chat",
            model_name="legacy-model",
            pricing_version="test-v1",
            enforced=True,
            reserved_input_tokens=1000,
            reserved_output_tokens=500,
            reserved_cost_micro_usd=100,
            prompt_chars=4,
            prompt_sha256="0" * 64,
            schema_sha256="0" * 64,
            lease_expires_at=iso_utc(utc_now() + timedelta(seconds=300)),
        )
        gateway.ledger.reserve(r)

    providers = gateway.providers
    assert isinstance(providers, FakeProviders)
    with pytest.raises(ModelBudgetExceeded):
        gateway.invoke_structured(
            task_kind="chat_answer",
            schema=FakeDraft,
            prompt="test prompt",
            node_name="test_node",
        )
    assert providers.chat_builds == 0


def test_structured_retry_usage_sums(tmp_path: Path):
    attempts = [
        _make_attempt(
            status="validation_error",
            token_usage={"prompt_tokens": 100, "completion_tokens": 20},
        ),
        _make_attempt(
            status="succeeded",
            token_usage={"prompt_tokens": 110, "completion_tokens": 30},
        ),
    ]
    result = _make_structured_result(attempts=attempts)
    gateway = _build_priced_gateway(
        tmp_path,
        mode="active",
        structured_invoker=_make_fake_invoker(result),
    )
    invocation = gateway.invoke_structured(
        task_kind="chat_answer",
        schema=FakeDraft,
        prompt="test prompt",
        node_name="test_node",
    )
    assert invocation.ledger_record is not None
    assert invocation.ledger_record.actual_input_tokens == 210
    assert invocation.ledger_record.actual_output_tokens == 50
    assert invocation.ledger_record.usage_quality == "provider_reported"
    assert invocation.ledger_record.provider_response_count == 2


def test_missing_usage_uses_upper_bound(tmp_path: Path):
    attempts = [
        _make_attempt(
            status="succeeded",
            token_usage=None,
        ),
    ]
    result = _make_structured_result(attempts=attempts)
    gateway = _build_priced_gateway(
        tmp_path,
        mode="active",
        structured_invoker=_make_fake_invoker(result),
    )
    invocation = gateway.invoke_structured(
        task_kind="chat_answer",
        schema=FakeDraft,
        prompt="test prompt",
        node_name="test_node",
    )
    assert invocation.ledger_record is not None
    assert invocation.ledger_record.usage_quality == "reservation_upper_bound"
    assert invocation.ledger_record.actual_input_tokens == (
        invocation.ledger_record.reserved_input_tokens
    )


def test_ledger_records_prompt_hash_but_not_prompt(tmp_path: Path):
    result = _make_structured_result()
    gateway = _build_priced_gateway(
        tmp_path,
        mode="active",
        structured_invoker=_make_fake_invoker(result),
    )
    invocation = gateway.invoke_structured(
        task_kind="chat_answer",
        schema=FakeDraft,
        prompt="secret prompt content",
        node_name="test_node",
    )
    record = invocation.ledger_record
    assert record is not None
    assert record.prompt_sha256 is not None
    assert len(record.prompt_sha256) == 64
    dumped = record.model_dump()
    for key in dumped:
        assert "secret" not in str(dumped[key]).lower() or key == "prompt_sha256"


def test_expected_decision_sha256_mismatch(tmp_path: Path):
    result = _make_structured_result()
    gateway = _build_priced_gateway(
        tmp_path,
        mode="active",
        structured_invoker=_make_fake_invoker(result),
    )
    from app.model_routing.errors import ModelRouteUnavailable

    with pytest.raises(ModelRouteUnavailable):
        gateway.invoke_structured(
            task_kind="chat_answer",
            schema=FakeDraft,
            prompt="test prompt",
            node_name="test_node",
            expected_decision_sha256="1" * 64,
        )
    assert gateway.providers.chat_builds == 0
