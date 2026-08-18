from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.model_routing.catalog import load_model_catalog
from app.model_routing.gateway import ModelGateway
from app.model_routing.policy import ModelRouter
from app.model_routing.repository import SqliteModelLedger
from app.model_routing.schemas import (
    ModelBudgetPolicy,
    ModelPricing,
    ModelProfile,
    ModelRouteRequest,
    ModelRoutingDocument,
    ModelTaskRoute,
)


TEST_PRICING = ModelPricing(
    pricing_version="test-v1",
    billing_mode="priced",
    input_micro_usd_per_million=1000,
    output_micro_usd_per_million=2000,
)

FREE_PRICING = ModelPricing(
    pricing_version="test-v1",
    billing_mode="free",
    input_micro_usd_per_million=0,
    output_micro_usd_per_million=0,
)

UNPRICED_PRICING = ModelPricing(
    pricing_version="test-v1",
    billing_mode="unpriced",
    input_micro_usd_per_million=None,
    output_micro_usd_per_million=None,
)

TEST_BUDGET = ModelBudgetPolicy(
    daily_total_token_limit=10000,
    daily_cost_limit_micro_usd=10000,
    per_job_total_token_limit=5000,
    per_job_cost_limit_micro_usd=5000,
    reservation_ttl_seconds=300,
    allow_unpriced_in_active=False,
)


class FakeProviders:
    """测试用 Provider Factory，避免解析真实 Secret。"""

    def __init__(self, *, chat: Any = None, embedding: Any = None):
        self.chat = chat
        self.embedding = embedding
        self.chat_builds = 0
        self.embedding_builds = 0

    def build_chat(self, profile: Any, *, max_output_tokens: int) -> Any:
        self.chat_builds += 1
        if self.chat is None:
            raise AssertionError("测试不允许构造 Chat Provider")
        return self.chat

    def build_embedding(self, profile: Any) -> Any:
        self.embedding_builds += 1
        if self.embedding is None:
            raise AssertionError("测试不允许构造 Embedding Provider")
        return self.embedding


class ScriptedModelGateway:
    """Node tests use the routed gateway contract without a real Provider."""

    def __init__(self, invocations: Any):
        self._invocations = invocations
        self.calls: list[dict[str, Any]] = []
        self.preview_calls: list[dict[str, Any]] = []
        self._decision = SimpleNamespace(
            decision_sha256="a" * 64,
            executed_profile_id="test_chat",
            executed_model_name="test-model",
        )

    def preview_structured(self, **kwargs: Any) -> Any:
        self.preview_calls.append(dict(kwargs))
        return self._decision

    def invoke_structured(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        if callable(self._invocations):
            result = self._invocations(**kwargs)
        else:
            if not self._invocations:
                raise AssertionError("ScriptedModelGateway responses exhausted")
            result = self._invocations.pop(0)
        return SimpleNamespace(
            result=result,
            value=result.value,
            attempts=result.attempts,
            method=result.method,
            strict=result.strict,
            max_retries=result.max_retries,
            succeeded=result.succeeded,
            decision=self._decision,
            invocation_id=None,
            ledger_record=None,
        )


def _legacy_chat_profile(
    pricing: ModelPricing | None = None,
) -> ModelProfile:
    return ModelProfile(
        profile_id="legacy_chat",
        workload_kind="chat",
        provider_binding="primary_chat",
        model_name="$OPENAI_MODEL",
        quality_tier="balanced",
        quality_rank=70,
        capabilities={
            "structured_json_schema",
            "structured_function_calling",
            "structured_json_mode",
            "long_context",
            "tool_calling",
        },
        context_window_tokens=32768,
        max_output_tokens=4096,
        thinking_mode="disabled",
        enabled=True,
        pricing=pricing or UNPRICED_PRICING,
    )


def _strong_chat_profile(
    pricing: ModelPricing | None = None,
) -> ModelProfile:
    return ModelProfile(
        profile_id="strong_chat",
        workload_kind="chat",
        provider_binding="primary_chat",
        model_name="$OPENAI_STRONG_MODEL",
        quality_tier="high",
        quality_rank=90,
        capabilities={
            "structured_json_schema",
            "structured_function_calling",
            "structured_json_mode",
            "long_context",
            "tool_calling",
        },
        context_window_tokens=32768,
        max_output_tokens=4096,
        thinking_mode="disabled",
        enabled=True,
        pricing=pricing or UNPRICED_PRICING,
    )


def _economy_chat_profile(
    pricing: ModelPricing | None = None,
) -> ModelProfile:
    return ModelProfile(
        profile_id="economy_chat",
        workload_kind="chat",
        provider_binding="primary_chat",
        model_name="$OPENAI_ECONOMY_MODEL",
        quality_tier="economy",
        quality_rank=60,
        capabilities={
            "structured_json_schema",
            "structured_function_calling",
            "structured_json_mode",
            "tool_calling",
        },
        context_window_tokens=32768,
        max_output_tokens=4096,
        thinking_mode="disabled",
        enabled=True,
        pricing=pricing or UNPRICED_PRICING,
    )


def _legacy_embedding_profile(
    pricing: ModelPricing | None = None,
) -> ModelProfile:
    return ModelProfile(
        profile_id="legacy_embedding",
        workload_kind="embedding",
        provider_binding="primary_embedding",
        model_name="$EMBEDDING_MODEL",
        quality_tier="balanced",
        quality_rank=70,
        capabilities={"embedding"},
        context_window_tokens=8192,
        max_output_tokens=0,
        thinking_mode=None,
        enabled=True,
        pricing=pricing or UNPRICED_PRICING,
    )


def build_test_document(
    *,
    budget: ModelBudgetPolicy | None = None,
    extra_profiles: list[ModelProfile] | None = None,
    pricing_override: dict[str, ModelPricing] | None = None,
) -> ModelRoutingDocument:
    pricing_map = pricing_override or {}
    profiles = [
        _legacy_chat_profile(pricing_map.get("legacy_chat")),
        _strong_chat_profile(pricing_map.get("strong_chat")),
        _economy_chat_profile(pricing_map.get("economy_chat")),
        _legacy_embedding_profile(pricing_map.get("legacy_embedding")),
    ]
    if extra_profiles:
        profiles.extend(extra_profiles)

    routes = [
        ModelTaskRoute(
            task_kind="paper_section_extraction",
            workload_kind="chat",
            required_capabilities={"long_context"},
            candidate_profile_ids=["strong_chat", "legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=70,
            max_input_tokens=24000,
            max_output_tokens=4096,
            validation_max_retries=2,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="paper_code_mapping",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["strong_chat", "legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=70,
            max_input_tokens=20000,
            max_output_tokens=4096,
            validation_max_retries=2,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="experiment_plan",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["legacy_chat", "strong_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=70,
            max_input_tokens=16000,
            max_output_tokens=4096,
            validation_max_retries=2,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="failure_debug",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["strong_chat", "legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=70,
            max_input_tokens=16000,
            max_output_tokens=4096,
            validation_max_retries=2,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="repair_plan",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["strong_chat", "legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=80,
            max_input_tokens=16000,
            max_output_tokens=4096,
            validation_max_retries=2,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="file_repair_plan",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["strong_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=80,
            max_input_tokens=16000,
            max_output_tokens=4096,
            validation_max_retries=1,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="chat_answer",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["legacy_chat", "strong_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=70,
            max_input_tokens=20000,
            max_output_tokens=4096,
            validation_max_retries=1,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="chat_tool_selection",
            workload_kind="chat",
            required_capabilities={"tool_calling"},
            candidate_profile_ids=["economy_chat", "legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=50,
            max_input_tokens=12000,
            max_output_tokens=768,
            validation_max_retries=0,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="chat_memory_compaction",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["economy_chat", "legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=50,
            max_input_tokens=16000,
            max_output_tokens=2048,
            validation_max_retries=1,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="code_embedding_document",
            workload_kind="embedding",
            required_capabilities={"embedding"},
            candidate_profile_ids=["legacy_embedding"],
            legacy_profile_id="legacy_embedding",
            minimum_quality_rank=60,
            max_input_tokens=8192,
            max_output_tokens=0,
            validation_max_retries=0,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="code_embedding_query",
            workload_kind="embedding",
            required_capabilities={"embedding"},
            candidate_profile_ids=["legacy_embedding"],
            legacy_profile_id="legacy_embedding",
            minimum_quality_rank=60,
            max_input_tokens=8192,
            max_output_tokens=0,
            validation_max_retries=0,
            provider_max_retries=2,
        ),
        ModelTaskRoute(
            task_kind="evaluation_probe",
            workload_kind="chat",
            required_capabilities=set(),
            candidate_profile_ids=["legacy_chat"],
            legacy_profile_id="legacy_chat",
            minimum_quality_rank=60,
            max_input_tokens=8000,
            max_output_tokens=2048,
            validation_max_retries=1,
            provider_max_retries=1,
        ),
    ]

    return ModelRoutingDocument(
        policy_version="test-v1",
        profiles=profiles,
        routes=routes,
        budget=budget or TEST_BUDGET,
    )


def write_test_policy(
    tmp_path: Path,
    document: ModelRoutingDocument | None = None,
) -> Path:
    """把测试 Policy JSON 写入 tmp_path 内的文件。"""
    doc = document or build_test_document()
    tmp_path.mkdir(parents=True, exist_ok=True)
    policy_path = tmp_path / "model_routing_policy.json"
    policy_path.write_text(
        json.dumps(doc.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    return policy_path


def build_test_catalog(
    tmp_path: Path,
    document: ModelRoutingDocument | None = None,
):
    policy_path = write_test_policy(tmp_path, document)
    return load_model_catalog(
        policy_path,
        allowed_root=tmp_path,
        substitutions={
            "$OPENAI_MODEL": "legacy-model",
            "$OPENAI_ECONOMY_MODEL": "economy-model",
            "$OPENAI_STRONG_MODEL": "strong-model",
            "$EMBEDDING_MODEL": "embedding-model",
        },
    )


def build_test_router(
    tmp_path: Path,
    document: ModelRoutingDocument | None = None,
) -> ModelRouter:
    catalog = build_test_catalog(tmp_path, document)
    return ModelRouter(catalog)


def build_test_gateway(
    tmp_path: Path,
    *,
    mode: str = "off",
    providers: FakeProviders | None = None,
    structured_invoker: Any = None,
    document: ModelRoutingDocument | None = None,
) -> ModelGateway:
    catalog = build_test_catalog(tmp_path, document)
    return ModelGateway(
        mode=mode,
        router=ModelRouter(catalog),
        ledger=SqliteModelLedger(
            tmp_path / "usage.sqlite",
            budget=catalog.document.budget,
        ),
        providers=providers or FakeProviders(),
        structured_method="json_schema",
        structured_strict=True,
        raw_preview_chars=200,
        provider_retry_base_seconds=0,
        structured_invoker=structured_invoker,
    )


def build_chat_route_request(
    *,
    task_kind: str = "chat_answer",
    estimated_input_tokens: int = 100,
    requested_max_output_tokens: int = 100,
    quality_tier: str = "balanced",
    required_capabilities: set[str] | None = None,
    node_name: str = "test_node",
    prompt_text: str = "test prompt for routing",
) -> ModelRouteRequest:
    from app.model_routing.identity import sha256_text, schema_sha256
    from pydantic import BaseModel

    class _DummySchema(BaseModel):
        pass

    caps = required_capabilities or {"structured_json_schema"}
    return ModelRouteRequest(
        task_kind=task_kind,
        workload_kind="chat",
        required_capabilities=caps,
        requested_quality_tier=quality_tier,
        estimated_input_tokens=estimated_input_tokens,
        requested_max_output_tokens=requested_max_output_tokens,
        prompt_sha256=sha256_text(prompt_text),
        prompt_chars=len(prompt_text),
        schema_name="_DummySchema",
        schema_sha256=schema_sha256(_DummySchema),
        node_name=node_name,
    )


def build_embedding_route_request(
    *,
    task_kind: str = "code_embedding_query",
    estimated_input_tokens: int = 100,
    node_name: str = "test_embedding_node",
    prompt_text: str = "test embedding query",
) -> ModelRouteRequest:
    from app.model_routing.identity import sha256_text

    return ModelRouteRequest(
        task_kind=task_kind,
        workload_kind="embedding",
        required_capabilities={"embedding"},
        requested_quality_tier="balanced",
        estimated_input_tokens=estimated_input_tokens,
        requested_max_output_tokens=0,
        prompt_sha256=sha256_text(prompt_text),
        prompt_chars=len(prompt_text),
        schema_name=None,
        schema_sha256=None,
        node_name=node_name,
    )
