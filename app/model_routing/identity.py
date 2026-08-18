from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from pydantic import BaseModel

from app.model_routing.errors import ModelUsageError
from app.model_routing.schemas import (
    ModelPricing,
    ModelRouteDecision,
    ModelRouteRequest,
)


def canonical_json(value: Any) -> str:
    """把模型、集合和普通对象转换成稳定 JSON。"""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")

    def normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                str(key): normalize(item[key])
                for key in sorted(item)
            }
        if isinstance(item, set):
            return sorted(normalize(value) for value in item)
        if isinstance(item, list):
            return [normalize(value) for value in item]
        return item

    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_text(canonical_json(value))


def estimate_text_tokens(text: str) -> int:
    """不下载 tokenizer 的保守预留：每个可见 UTF-8 字节预留一个 Token。"""

    byte_count = len(text.encode("utf-8"))
    return max(1, byte_count)


def estimate_texts_tokens(texts: list[str]) -> int:
    if not texts:
        raise ModelUsageError("Embedding texts 不能为空")
    return sum(estimate_text_tokens(text) for text in texts)


def schema_sha256(schema: type[BaseModel]) -> str:
    return sha256_value(schema.model_json_schema())


def request_sha256(request: ModelRouteRequest) -> str:
    return sha256_value(request)


def calculate_cost_micro_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    pricing: ModelPricing,
) -> int | None:
    if input_tokens < 0 or output_tokens < 0:
        raise ModelUsageError("Token 数不能为负数")
    if pricing.billing_mode == "unpriced":
        return None
    if pricing.billing_mode == "free":
        return 0

    input_rate = pricing.input_micro_usd_per_million
    output_rate = pricing.output_micro_usd_per_million
    if input_rate is None or output_rate is None:
        raise ModelUsageError("priced profile 缺少价格")

    numerator = (
        input_tokens * input_rate
        + output_tokens * output_rate
    )
    return math.ceil(numerator / 1_000_000)


def build_decision_sha256(
    decision: ModelRouteDecision,
) -> str:
    payload = decision.model_dump(mode="json")
    payload.pop("decision_sha256", None)
    return sha256_value(payload)


def validate_decision_sha256(
    decision: ModelRouteDecision,
) -> None:
    if build_decision_sha256(decision) != decision.decision_sha256:
        raise ValueError("ModelRouteDecision hash 不一致")
