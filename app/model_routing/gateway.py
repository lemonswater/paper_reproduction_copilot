from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Generic, TypeVar

from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from app.model_routing.errors import ModelRouteUnavailable
from app.model_routing.identity import (
    canonical_json,
    calculate_cost_micro_usd,
    estimate_text_tokens,
    estimate_texts_tokens,
    request_sha256,
    schema_sha256,
    sha256_text,
    sha256_value,
)
from app.model_routing.policy import ModelRouter
from app.model_routing.provider import ProviderFactoryPort
from app.model_routing.repository import (
    SqliteModelLedger,
    iso_utc,
    utc_now,
)
from app.model_routing.schemas import (
    ModelCapability,
    ModelInvocationRecord,
    ModelProfile,
    ModelQualityTier,
    ModelReservationRequest,
    ModelRouteDecision,
    ModelRouteRequest,
    ModelRoutingMode,
    ModelTaskKind,
    ModelUsage,
)
from app.model_routing.usage import (
    estimated_embedding_usage,
    usage_from_ai_message,
    usage_from_structured_attempts,
)
from app.tools.structured_output_tools import (
    StructuredInvocationResult,
    invoke_structured_with_retry,
)


SchemaT = TypeVar("SchemaT", bound=BaseModel)
EmbeddingT = TypeVar("EmbeddingT")
StructuredInvoker = Callable[..., StructuredInvocationResult[Any]]


@dataclass(frozen=True)
class RoutedStructuredInvocation(Generic[SchemaT]):
    """保持旧 result 属性，降低节点接线改动量。"""

    result: StructuredInvocationResult[SchemaT]
    decision: ModelRouteDecision
    invocation_id: str | None
    ledger_record: ModelInvocationRecord | None

    @property
    def value(self) -> SchemaT | None:
        return self.result.value

    @property
    def attempts(self) -> list[Any]:
        return self.result.attempts

    @property
    def method(self) -> str:
        return self.result.method

    @property
    def strict(self) -> bool | None:
        return self.result.strict

    @property
    def max_retries(self) -> int:
        return self.result.max_retries

    @property
    def provider_max_retries(self) -> int:
        return self.result.provider_max_retries

    @property
    def provider_retry_base_seconds(self) -> float:
        return self.result.provider_retry_base_seconds

    @property
    def succeeded(self) -> bool:
        return self.result.succeeded


@dataclass(frozen=True)
class RoutedEmbeddingInvocation(Generic[EmbeddingT]):
    value: EmbeddingT
    decision: ModelRouteDecision
    invocation_id: str | None
    ledger_record: ModelInvocationRecord | None


@dataclass(frozen=True)
class RoutedToolCallingInvocation:
    message: AIMessage
    decision: ModelRouteDecision
    invocation_id: str | None
    ledger_record: ModelInvocationRecord | None


def _structured_capability(method: str) -> ModelCapability:
    mapping: dict[str, ModelCapability] = {
        "json_schema": "structured_json_schema",
        "function_calling": "structured_function_calling",
        "json_mode": "structured_json_mode",
    }
    try:
        return mapping[method]
    except KeyError as exc:
        raise ValueError(f"未知 structured output method：{method}") from exc


def _safe_error_code(prefix: str, error: BaseException) -> str:
    # 只保留类型名，绝不保存 Provider 原始 message。
    normalized = "".join(
        character if character.isalnum() else "_"
        for character in type(error).__name__.upper()
    ).strip("_")
    return f"{prefix}_{normalized}"[:120]


def _is_transient_provider_error(error: BaseException) -> bool:
    material = (
        f"{type(error).__module__}.{type(error).__name__}: {error}"
    ).lower()
    return any(
        marker in material
        for marker in (
            "timeout",
            "connection",
            "rate_limit",
            "ratelimit",
            "429",
            "502",
            "503",
            "504",
            "temporarily unavailable",
        )
    )


def _message_for_hash(message: BaseMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": message.type,
        "content": message.content,
    }
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id is not None:
        payload["tool_call_id"] = tool_call_id
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        payload["tool_calls"] = tool_calls
    return payload


def _tool_prompt_material(
    *,
    messages: list[BaseMessage],
    tools: list[dict[str, Any]],
) -> str:
    return canonical_json(
        {
            "messages": [_message_for_hash(item) for item in messages],
            "tools": tools,
        }
    )


class ModelGateway:
    def __init__(
        self,
        *,
        mode: ModelRoutingMode,
        router: ModelRouter,
        ledger: SqliteModelLedger,
        providers: ProviderFactoryPort,
        structured_method: str,
        structured_strict: bool,
        raw_preview_chars: int,
        provider_retry_base_seconds: float,
        structured_invoker: StructuredInvoker = invoke_structured_with_retry,
    ) -> None:
        self.mode = mode
        self.router = router
        self.ledger = ledger
        self.providers = providers
        self.structured_method = structured_method
        self.structured_strict = structured_strict
        self.raw_preview_chars = raw_preview_chars
        self.provider_retry_base_seconds = provider_retry_base_seconds
        self.structured_invoker = structured_invoker

    def _reservation(
        self,
        *,
        request: ModelRouteRequest,
        decision: ModelRouteDecision,
        profile: ModelProfile,
        invocation_id: str,
    ) -> ModelReservationRequest:
        max_attempts = decision.max_billable_attempts
        reserved_input = request.estimated_input_tokens * max_attempts
        reserved_output = request.requested_max_output_tokens * max_attempts
        reserved_cost = calculate_cost_micro_usd(
            input_tokens=reserved_input,
            output_tokens=reserved_output,
            pricing=profile.pricing,
        )
        expires = utc_now() + timedelta(
            seconds=(
                self.router.catalog.document.budget.reservation_ttl_seconds
            )
        )
        return ModelReservationRequest(
            invocation_id=invocation_id,
            request_sha256=request_sha256(request),
            decision_sha256=decision.decision_sha256,
            task_kind=request.task_kind,
            job_id=request.job_id,
            run_id=request.run_id,
            node_name=request.node_name,
            profile_id=profile.profile_id,
            model_name=profile.model_name,
            pricing_version=profile.pricing.pricing_version,
            enforced=self.mode == "active",
            reserved_input_tokens=reserved_input,
            reserved_output_tokens=reserved_output,
            reserved_cost_micro_usd=reserved_cost,
            prompt_chars=request.prompt_chars,
            prompt_sha256=request.prompt_sha256,
            schema_sha256=request.schema_sha256,
            lease_expires_at=iso_utc(expires),
        )

    def _build_structured_request(
        self,
        *,
        task_kind: ModelTaskKind,
        schema: type[BaseModel],
        prompt: str,
        node_name: str,
        job_id: str | None,
        run_id: str | None,
        quality_tier: ModelQualityTier,
        requested_max_output_tokens: int | None,
    ) -> ModelRouteRequest:
        route = self.router.catalog.route(task_kind)
        max_output = (
            route.max_output_tokens
            if requested_max_output_tokens is None
            else requested_max_output_tokens
        )
        # Structured Schema、retry raw preview 和错误说明也会进入请求上下文，
        # 不能只按业务 Prompt 估算 input token。
        schema_text = canonical_json(schema.model_json_schema())
        estimated_input = (
            estimate_text_tokens(prompt)
            + estimate_text_tokens(schema_text)
            + self.raw_preview_chars
            + 2048
        )
        return ModelRouteRequest(
            task_kind=task_kind,
            workload_kind="chat",
            required_capabilities={
                _structured_capability(self.structured_method)
            },
            requested_quality_tier=quality_tier,
            estimated_input_tokens=estimated_input,
            requested_max_output_tokens=max_output,
            prompt_sha256=sha256_text(prompt),
            prompt_chars=len(prompt),
            schema_name=schema.__name__,
            schema_sha256=schema_sha256(schema),
            job_id=job_id,
            run_id=run_id,
            node_name=node_name,
        )

    def preview_structured(
        self,
        *,
        task_kind: ModelTaskKind,
        schema: type[BaseModel],
        prompt: str,
        node_name: str,
        job_id: str | None = None,
        run_id: str | None = None,
        quality_tier: ModelQualityTier = "balanced",
        requested_max_output_tokens: int | None = None,
    ) -> ModelRouteDecision:
        """只做确定性路由，不预留预算、不解析 Secret、不调用 Provider。"""

        request = self._build_structured_request(
            task_kind=task_kind,
            schema=schema,
            prompt=prompt,
            node_name=node_name,
            job_id=job_id,
            run_id=run_id,
            quality_tier=quality_tier,
            requested_max_output_tokens=requested_max_output_tokens,
        )
        decision, _ = self.router.route(request=request, mode=self.mode)
        return decision

    def invoke_structured(
        self,
        *,
        task_kind: ModelTaskKind,
        schema: type[SchemaT],
        prompt: str,
        node_name: str,
        job_id: str | None = None,
        run_id: str | None = None,
        quality_tier: ModelQualityTier = "balanced",
        requested_max_output_tokens: int | None = None,
        expected_decision_sha256: str | None = None,
    ) -> RoutedStructuredInvocation[SchemaT]:
        route = self.router.catalog.route(task_kind)
        request = self._build_structured_request(
            task_kind=task_kind,
            schema=schema,
            prompt=prompt,
            node_name=node_name,
            job_id=job_id,
            run_id=run_id,
            quality_tier=quality_tier,
            requested_max_output_tokens=requested_max_output_tokens,
        )
        max_output = request.requested_max_output_tokens
        decision, profile = self.router.route(
            request=request,
            mode=self.mode,
        )
        if (
            expected_decision_sha256 is not None
            and decision.decision_sha256 != expected_decision_sha256
        ):
            raise ModelRouteUnavailable("MODEL_ROUTE_DECISION_STALE")
        invocation_id = f"mdl_{uuid.uuid4().hex}"
        reservation = self._reservation(
            request=request,
            decision=decision,
            profile=profile,
            invocation_id=invocation_id,
        )

        record: ModelInvocationRecord | None = None
        if self.mode != "off":
            # active 的预算拒绝发生在 Secret 解析和 Provider Client 构造之前。
            record = self.ledger.reserve(reservation)

        started = time.monotonic()
        try:
            llm = self.providers.build_chat(
                profile,
                max_output_tokens=max_output,
            )
        except Exception as exc:
            if self.mode != "off":
                usage = ModelUsage(
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_micro_usd=calculate_cost_micro_usd(
                        input_tokens=0,
                        output_tokens=0,
                        pricing=profile.pricing,
                    ),
                    quality="not_applicable",
                    provider_response_count=0,
                )
                self.ledger.settle(
                    invocation_id=invocation_id,
                    status="failed",
                    usage=usage,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_code=_safe_error_code("MODEL_CLIENT", exc),
                )
            raise

        try:
            result = self.structured_invoker(
                llm=llm,
                schema=schema,
                prompt=prompt,
                method=self.structured_method,
                strict=self.structured_strict,
                max_retries=route.validation_max_retries,
                raw_preview_chars=self.raw_preview_chars,
                provider_max_retries=route.provider_max_retries,
                provider_retry_base_seconds=(
                    self.provider_retry_base_seconds
                ),
                telemetry_provider_label=profile.provider_binding,
                telemetry_model_name=profile.model_name,
            )
        except Exception as exc:
            if self.mode != "off":
                upper_bound = ModelUsage(
                    input_tokens=reservation.reserved_input_tokens,
                    output_tokens=reservation.reserved_output_tokens,
                    total_tokens=reservation.reserved_total_tokens,
                    cost_micro_usd=reservation.reserved_cost_micro_usd,
                    quality="reservation_upper_bound",
                    provider_response_count=0,
                )
                record = self.ledger.settle(
                    invocation_id=invocation_id,
                    status="usage_unknown",
                    usage=upper_bound,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_code=_safe_error_code("MODEL_INVOKE", exc),
                )
            raise

        if self.mode != "off":
            usage = usage_from_structured_attempts(
                attempts=result.attempts,
                reserved_input_tokens=reservation.reserved_input_tokens,
                reserved_output_tokens=reservation.reserved_output_tokens,
                reserved_cost_micro_usd=(
                    reservation.reserved_cost_micro_usd
                ),
                pricing=profile.pricing,
            )
            status = "succeeded" if result.value is not None else "failed"
            error_code = (
                None
                if result.value is not None
                else "MODEL_STRUCTURED_OUTPUT_FAILED"
            )
            record = self.ledger.settle(
                invocation_id=invocation_id,
                status=status,
                usage=usage,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code=error_code,
            )

        return RoutedStructuredInvocation(
            result=result,
            decision=decision,
            invocation_id=(None if self.mode == "off" else invocation_id),
            ledger_record=record,
        )

    def _build_tool_request(
        self,
        *,
        messages: list[BaseMessage],
        tools: list[dict[str, Any]],
        node_name: str,
        job_id: str,
        quality_tier: ModelQualityTier,
        requested_max_output_tokens: int,
    ) -> ModelRouteRequest:
        material = _tool_prompt_material(
            messages=messages,
            tools=tools,
        )
        return ModelRouteRequest(
            task_kind="chat_tool_selection",
            workload_kind="chat",
            required_capabilities={"tool_calling"},
            requested_quality_tier=quality_tier,
            estimated_input_tokens=(
                estimate_text_tokens(material) + 1024
            ),
            requested_max_output_tokens=requested_max_output_tokens,
            prompt_sha256=sha256_text(material),
            prompt_chars=len(material),
            schema_name="ProviderToolCatalog",
            schema_sha256=sha256_value(tools),
            job_id=job_id,
            run_id=None,
            node_name=node_name,
        )

    def invoke_tool_calling(
        self,
        *,
        messages: list[BaseMessage],
        tools: list[dict[str, Any]],
        node_name: str,
        job_id: str,
        quality_tier: ModelQualityTier = "economy",
        requested_max_output_tokens: int = 768,
    ) -> RoutedToolCallingInvocation:
        if not messages:
            raise ValueError("Tool Calling messages 不能为空")
        if not tools:
            raise ValueError("Tool Calling tools 不能为空")

        route = self.router.catalog.route("chat_tool_selection")
        request = self._build_tool_request(
            messages=messages,
            tools=tools,
            node_name=node_name,
            job_id=job_id,
            quality_tier=quality_tier,
            requested_max_output_tokens=requested_max_output_tokens,
        )
        decision, profile = self.router.route(
            request=request,
            mode=self.mode,
        )
        invocation_id = f"mdl_{uuid.uuid4().hex}"
        reservation = self._reservation(
            request=request,
            decision=decision,
            profile=profile,
            invocation_id=invocation_id,
        )

        record: ModelInvocationRecord | None = None
        if self.mode != "off":
            record = self.ledger.reserve(reservation)

        started = time.monotonic()
        try:
            llm = self.providers.build_chat(
                profile,
                max_output_tokens=request.requested_max_output_tokens,
            )
            bound = llm.bind_tools(
                tools,
                tool_choice="auto",
                strict=True,
                parallel_tool_calls=False,
            )
        except Exception as exc:
            if self.mode != "off":
                zero_usage = ModelUsage(
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_micro_usd=calculate_cost_micro_usd(
                        input_tokens=0,
                        output_tokens=0,
                        pricing=profile.pricing,
                    ),
                    quality="not_applicable",
                    provider_response_count=0,
                )
                self.ledger.settle(
                    invocation_id=invocation_id,
                    status="failed",
                    usage=zero_usage,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_code=_safe_error_code("MODEL_TOOL_BIND", exc),
                )
            raise

        message: AIMessage | None = None
        had_provider_retry = False
        try:
            for retry_index in range(route.provider_max_retries + 1):
                try:
                    candidate = bound.invoke(messages)
                    if not isinstance(candidate, AIMessage):
                        raise TypeError("Tool Provider 未返回 AIMessage")
                    message = candidate
                    break
                except Exception as exc:
                    can_retry = (
                        _is_transient_provider_error(exc)
                        and retry_index < route.provider_max_retries
                    )
                    if not can_retry:
                        raise
                    had_provider_retry = True
                    time.sleep(
                        self.provider_retry_base_seconds * (2**retry_index)
                    )
        except Exception as exc:
            if self.mode != "off":
                upper_bound = ModelUsage(
                    input_tokens=reservation.reserved_input_tokens,
                    output_tokens=reservation.reserved_output_tokens,
                    total_tokens=reservation.reserved_total_tokens,
                    cost_micro_usd=reservation.reserved_cost_micro_usd,
                    quality="reservation_upper_bound",
                    provider_response_count=0,
                )
                record = self.ledger.settle(
                    invocation_id=invocation_id,
                    status="usage_unknown",
                    usage=upper_bound,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_code=_safe_error_code("MODEL_TOOL_INVOKE", exc),
                )
            raise

        if message is None:
            raise AssertionError("Tool Calling retry loop 未产生结果")

        if self.mode != "off":
            usage = usage_from_ai_message(
                message=message,
                reserved_input_tokens=reservation.reserved_input_tokens,
                reserved_output_tokens=reservation.reserved_output_tokens,
                reserved_cost_micro_usd=reservation.reserved_cost_micro_usd,
                pricing=profile.pricing,
                had_provider_retry=had_provider_retry,
            )
            record = self.ledger.settle(
                invocation_id=invocation_id,
                status="succeeded",
                usage=usage,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code=None,
            )

        return RoutedToolCallingInvocation(
            message=message,
            decision=decision,
            invocation_id=(None if self.mode == "off" else invocation_id),
            ledger_record=record,
        )

    def invoke_embedding(
        self,
        *,
        task_kind: ModelTaskKind,
        texts: list[str],
        node_name: str,
        invoke: Callable[[ModelProfile], EmbeddingT],
        job_id: str | None = None,
        run_id: str | None = None,
    ) -> RoutedEmbeddingInvocation[EmbeddingT]:
        if task_kind not in {
            "code_embedding_document",
            "code_embedding_query",
        }:
            raise ValueError("invoke_embedding 收到非 Embedding task")
        estimated = estimate_texts_tokens(texts)
        request = ModelRouteRequest(
            task_kind=task_kind,
            workload_kind="embedding",
            required_capabilities={"embedding"},
            requested_quality_tier="balanced",
            estimated_input_tokens=estimated,
            requested_max_output_tokens=0,
            prompt_sha256=sha256_value(texts),
            prompt_chars=sum(len(text) for text in texts),
            schema_name=None,
            schema_sha256=None,
            job_id=job_id,
            run_id=run_id,
            node_name=node_name,
        )
        decision, profile = self.router.route(
            request=request,
            mode=self.mode,
        )
        invocation_id = f"mdl_{uuid.uuid4().hex}"
        reservation = self._reservation(
            request=request,
            decision=decision,
            profile=profile,
            invocation_id=invocation_id,
        )

        record: ModelInvocationRecord | None = None
        if self.mode != "off":
            record = self.ledger.reserve(reservation)

        route = self.router.catalog.route(task_kind)
        started = time.monotonic()
        last_error: BaseException | None = None
        attempted = 0
        for retry_index in range(route.provider_max_retries + 1):
            attempted += 1
            try:
                value = invoke(profile)
                break
            except Exception as exc:
                last_error = exc
                can_retry = (
                    _is_transient_provider_error(exc)
                    and retry_index < route.provider_max_retries
                )
                if not can_retry:
                    if self.mode != "off":
                        upper_bound = ModelUsage(
                            input_tokens=reservation.reserved_input_tokens,
                            output_tokens=0,
                            total_tokens=reservation.reserved_input_tokens,
                            cost_micro_usd=(
                                reservation.reserved_cost_micro_usd
                            ),
                            quality="reservation_upper_bound",
                            provider_response_count=0,
                        )
                        record = self.ledger.settle(
                            invocation_id=invocation_id,
                            status="usage_unknown",
                            usage=upper_bound,
                            latency_ms=int(
                                (time.monotonic() - started) * 1000
                            ),
                            error_code=_safe_error_code(
                                "MODEL_EMBEDDING",
                                exc,
                            ),
                        )
                    raise
                time.sleep(
                    self.provider_retry_base_seconds * (2**retry_index)
                )
        else:
            raise AssertionError("Embedding retry loop reached invalid state")

        if last_error is not None and attempted > 1:
            usage = ModelUsage(
                input_tokens=reservation.reserved_input_tokens,
                output_tokens=0,
                total_tokens=reservation.reserved_input_tokens,
                cost_micro_usd=reservation.reserved_cost_micro_usd,
                quality="reservation_upper_bound",
                provider_response_count=1,
            )
        else:
            usage = estimated_embedding_usage(
                input_tokens=estimated,
                pricing=profile.pricing,
            )

        if self.mode != "off":
            record = self.ledger.settle(
                invocation_id=invocation_id,
                status="succeeded",
                usage=usage,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code=None,
            )
        return RoutedEmbeddingInvocation(
            value=value,
            decision=decision,
            invocation_id=(None if self.mode == "off" else invocation_id),
            ledger_record=record,
        )
