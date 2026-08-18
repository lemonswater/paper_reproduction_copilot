"""Phase 50: Model Routing Schema 与 Identity 工具测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.model_routing.identity import (
    calculate_cost_micro_usd,
    canonical_json,
    estimate_text_tokens,
    estimate_texts_tokens,
    sha256_text,
    sha256_value,
)
from app.model_routing.schemas import (
    ModelPricing,
    ModelUsage,
)


def test_priced_profile_requires_both_prices():
    with pytest.raises(ValidationError):
        ModelPricing(
            pricing_version="v1",
            billing_mode="priced",
            input_micro_usd_per_million=100,
            output_micro_usd_per_million=None,
        )


def test_priced_profile_requires_input_price():
    with pytest.raises(ValidationError):
        ModelPricing(
            pricing_version="v1",
            billing_mode="priced",
            input_micro_usd_per_million=None,
            output_micro_usd_per_million=200,
        )


def test_unpriced_profile_rejects_guessed_price():
    with pytest.raises(ValidationError):
        ModelPricing(
            pricing_version="v1",
            billing_mode="unpriced",
            input_micro_usd_per_million=100,
            output_micro_usd_per_million=None,
        )


def test_free_profile_rejects_nonzero_price():
    with pytest.raises(ValidationError):
        ModelPricing(
            pricing_version="v1",
            billing_mode="free",
            input_micro_usd_per_million=10,
            output_micro_usd_per_million=0,
        )


def test_free_profile_accepts_zero_prices():
    pricing = ModelPricing(
        pricing_version="v1",
        billing_mode="free",
        input_micro_usd_per_million=0,
        output_micro_usd_per_million=0,
    )
    assert pricing.billing_mode == "free"


def test_cost_uses_integer_micro_usd_round_up():
    pricing = ModelPricing(
        pricing_version="v1",
        billing_mode="priced",
        input_micro_usd_per_million=1000,
        output_micro_usd_per_million=2000,
    )
    # (1*1000 + 1*2000) / 1_000_000 = 0.003 -> ceil -> 1
    assert calculate_cost_micro_usd(
        input_tokens=1,
        output_tokens=1,
        pricing=pricing,
    ) == 1


def test_cost_zero_tokens():
    pricing = ModelPricing(
        pricing_version="v1",
        billing_mode="priced",
        input_micro_usd_per_million=1000,
        output_micro_usd_per_million=2000,
    )
    assert calculate_cost_micro_usd(
        input_tokens=0,
        output_tokens=0,
        pricing=pricing,
    ) == 0


def test_cost_unpriced_returns_none():
    pricing = ModelPricing(
        pricing_version="v1",
        billing_mode="unpriced",
    )
    assert calculate_cost_micro_usd(
        input_tokens=100,
        output_tokens=50,
        pricing=pricing,
    ) is None


def test_cost_free_returns_zero():
    pricing = ModelPricing(
        pricing_version="v1",
        billing_mode="free",
        input_micro_usd_per_million=0,
        output_micro_usd_per_million=0,
    )
    assert calculate_cost_micro_usd(
        input_tokens=100,
        output_tokens=50,
        pricing=pricing,
    ) == 0


def test_cost_negative_tokens_raises():
    pricing = ModelPricing(
        pricing_version="v1",
        billing_mode="priced",
        input_micro_usd_per_million=1000,
        output_micro_usd_per_million=2000,
    )
    from app.model_routing.errors import ModelUsageError

    with pytest.raises(ModelUsageError):
        calculate_cost_micro_usd(
            input_tokens=-1,
            output_tokens=0,
            pricing=pricing,
        )


def test_token_estimator_handles_chinese_and_empty_text():
    assert estimate_text_tokens("时空点云") >= 1
    assert estimate_text_tokens("") == 1


def test_token_estimator_ascii():
    assert estimate_text_tokens("hello") == 5


def test_estimate_texts_tokens_sums():
    assert estimate_texts_tokens(["abc", "de"]) == 5


def test_estimate_texts_tokens_empty_raises():
    from app.model_routing.errors import ModelUsageError

    with pytest.raises(ModelUsageError):
        estimate_texts_tokens([])


def test_usage_total_tokens_must_match():
    with pytest.raises(ValidationError):
        ModelUsage(
            input_tokens=10,
            output_tokens=20,
            total_tokens=25,
            quality="provider_reported",
            provider_response_count=1,
        )


def test_usage_negative_tokens_rejected():
    with pytest.raises(ValidationError):
        ModelUsage(
            input_tokens=-1,
            output_tokens=0,
            total_tokens=-1,
            quality="provider_reported",
            provider_response_count=1,
        )


def test_canonical_json_stable():
    data = {"b": 1, "a": 2}
    assert canonical_json(data) == '{"a":2,"b":1}'


def test_canonical_json_set_sorted():
    data = {"items": {"c", "a", "b"}}
    result = canonical_json(data)
    assert '"a"' in result
    assert '"b"' in result
    assert '"c"' in result


def test_sha256_text_stable():
    assert sha256_text("hello") == sha256_text("hello")
    assert sha256_text("hello") != sha256_text("world")


def test_sha256_value_dict():
    h1 = sha256_value({"a": 1, "b": 2})
    h2 = sha256_value({"b": 2, "a": 1})
    assert h1 == h2


def test_schema_forbid_extra_fields():
    with pytest.raises(ValidationError):
        ModelPricing(
            pricing_version="v1",
            billing_mode="priced",
            input_micro_usd_per_million=100,
            output_micro_usd_per_million=200,
            unknown_field="bad",
        )
