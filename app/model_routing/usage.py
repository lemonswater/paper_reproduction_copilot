from __future__ import annotations

from typing import Any

from app.model_routing.identity import calculate_cost_micro_usd
from app.model_routing.schemas import (
    ModelPricing,
    ModelUsage,
)


def _usage_int(
    usage: dict[str, Any],
    *names: str,
) -> int | None:
    for name in names:
        value = usage.get(name)
        if value is None:
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None
    return None


def usage_from_structured_attempts(
    *,
    attempts: list[Any],
    reserved_input_tokens: int,
    reserved_output_tokens: int,
    reserved_cost_micro_usd: int | None,
    pricing: ModelPricing,
) -> ModelUsage:
    """汇总每个真正收到响应的 Structured Output attempt。"""

    input_tokens = 0
    output_tokens = 0
    response_count = 0
    incomplete = False
    request_may_have_been_sent = False

    for attempt in attempts:
        status = getattr(attempt, "status", "")
        usage = getattr(attempt, "token_usage", None)
        if status in {
            "provider_retry",
            "invoke_error",
            "validation_error",
            "succeeded",
        }:
            request_may_have_been_sent = True

        if not isinstance(usage, dict):
            if status in {"validation_error", "succeeded"}:
                incomplete = True
            if status in {"provider_retry", "invoke_error"}:
                incomplete = True
            continue

        prompt = _usage_int(usage, "prompt_tokens", "input_tokens")
        completion = _usage_int(
            usage,
            "completion_tokens",
            "output_tokens",
        )
        if prompt is None or completion is None:
            incomplete = True
            continue
        input_tokens += prompt
        output_tokens += completion
        response_count += 1

    if request_may_have_been_sent and (incomplete or response_count == 0):
        return ModelUsage(
            input_tokens=reserved_input_tokens,
            output_tokens=reserved_output_tokens,
            total_tokens=reserved_input_tokens + reserved_output_tokens,
            cost_micro_usd=reserved_cost_micro_usd,
            quality="reservation_upper_bound",
            provider_response_count=response_count,
        )

    if not request_may_have_been_sent:
        return ModelUsage(
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_micro_usd=calculate_cost_micro_usd(
                input_tokens=0,
                output_tokens=0,
                pricing=pricing,
            ),
            quality="not_applicable",
            provider_response_count=0,
        )

    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_micro_usd=calculate_cost_micro_usd(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            pricing=pricing,
        ),
        quality="provider_reported",
        provider_response_count=response_count,
    )


def estimated_embedding_usage(
    *,
    input_tokens: int,
    pricing: ModelPricing,
) -> ModelUsage:
    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=0,
        total_tokens=input_tokens,
        cost_micro_usd=calculate_cost_micro_usd(
            input_tokens=input_tokens,
            output_tokens=0,
            pricing=pricing,
        ),
        quality="estimated",
        provider_response_count=1,
    )


def usage_from_ai_message(
    *,
    message: Any,
    reserved_input_tokens: int,
    reserved_output_tokens: int,
    reserved_cost_micro_usd: int | None,
    pricing: ModelPricing,
    had_provider_retry: bool,
) -> ModelUsage:
    """从成功 AIMessage 结算一次 Tool Selection 调用。"""

    if had_provider_retry:
        return ModelUsage(
            input_tokens=reserved_input_tokens,
            output_tokens=reserved_output_tokens,
            total_tokens=(reserved_input_tokens + reserved_output_tokens),
            cost_micro_usd=reserved_cost_micro_usd,
            quality="reservation_upper_bound",
            provider_response_count=1,
        )

    usage = getattr(message, "usage_metadata", None)
    if not isinstance(usage, dict):
        return ModelUsage(
            input_tokens=reserved_input_tokens,
            output_tokens=reserved_output_tokens,
            total_tokens=(reserved_input_tokens + reserved_output_tokens),
            cost_micro_usd=reserved_cost_micro_usd,
            quality="reservation_upper_bound",
            provider_response_count=1,
        )

    input_tokens = _usage_int(usage, "input_tokens", "prompt_tokens")
    output_tokens = _usage_int(
        usage,
        "output_tokens",
        "completion_tokens",
    )
    if input_tokens is None or output_tokens is None:
        return ModelUsage(
            input_tokens=reserved_input_tokens,
            output_tokens=reserved_output_tokens,
            total_tokens=(reserved_input_tokens + reserved_output_tokens),
            cost_micro_usd=reserved_cost_micro_usd,
            quality="reservation_upper_bound",
            provider_response_count=1,
        )

    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_micro_usd=calculate_cost_micro_usd(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            pricing=pricing,
        ),
        quality="provider_reported",
        provider_response_count=1,
    )
