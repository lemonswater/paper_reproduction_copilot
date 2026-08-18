from __future__ import annotations

"""Phase 28 测试/开发态使用的内存 Telemetry adapter。

核心价值：
- 断言 span/metric 调用发生（例如 Worker claim 在异常时是否 record_exception）。
- 防止业务代码给 metric 加了允许列表以外的高基数 label。
"""


import threading
import time
from contextlib import contextmanager
from typing import Any

from app.observability.ports import SpanPort, TelemetryPort
from app.observability.schemas import (
    MetricPoint,
    SpanLink,
    TraceCarrier,
)

ALLOWED_METRIC_ATTRIBUTES: dict[str, frozenset[str]] = {
    "paper_copilot_http_requests_total": frozenset(
        {"method", "route", "status_class"}
    ),
    "paper_copilot_jobs_submitted_total": frozenset(
        {"outcome"}
    ),
    "paper_copilot_jobs_claim_total": frozenset(
        {"outcome"}
    ),
    "paper_copilot_job_status_total": frozenset(
        {"status", "source"}
    ),
    "paper_copilot_nodes_entered_total": frozenset(
        {"node", "outcome"}
    ),
    "paper_copilot_prompt_completion_tokens_total": frozenset(
        {"provider", "model_family"}
    ),
    "paper_copilot_http_request_duration_seconds": frozenset(
        {"method", "route", "status_class"}
    ),
    "paper_copilot_job_execution_duration_seconds": frozenset(
        {"outcome", "execution_backend"}
    ),
    "paper_copilot_container_runtime_seconds": frozenset(
        {"backend", "outcome"}
    ),
    "paper_copilot_worker_claim_duration_seconds": frozenset(
        {"outcome"}
    ),
    "paper_copilot_workers_registered_total": frozenset(
        {"backend"}
    ),
}

# Phase 50：模型路由新增 input/output 独立指标。
ALLOWED_METRIC_ATTRIBUTES.update({
    "paper_copilot_prompt_tokens_total": frozenset(
        {"provider", "model_family"}
    ),
    "paper_copilot_completion_tokens_total": frozenset(
        {"provider", "model_family"}
    ),
})

# Phase 56：MCP 指标只允许固定 operation/outcome，不允许 Job 或请求身份。
ALLOWED_METRIC_ATTRIBUTES.update(
    {
        "paper_copilot_mcp_export_calls_total": frozenset(
            {"operation", "outcome"}
        ),
        "paper_copilot_mcp_export_duration_seconds": frozenset(
            {"operation", "outcome"}
        ),
    }
)

FORBIDDEN_METRIC_KEYS = {
    "job_id",
    "run_id",
    "request_id",
    "api_key",
    "claim_token_hash",
    "model",
    "user_agent",
}


def validate_metric_attributes(
    name: str, attributes: dict[str, str]
) -> None:
    allowed = ALLOWED_METRIC_ATTRIBUTES.get(name)
    if allowed is None:
        raise ValueError(
            f"metric 未登记：{name}"
        )
    keys = set(attributes)
    if keys - allowed:
        raise ValueError(
            f"metric {name} 有未登记属性："
            f"{sorted(keys - allowed)}"
        )
    if keys & FORBIDDEN_METRIC_KEYS:
        raise ValueError(
            "metric attributes 含高基数或敏感身份"
        )


class InMemorySpan(SpanPort):
    def __init__(
        self,
        name: str,
        attributes: dict[str, Any] | None,
        links: list[SpanLink] | None,
    ) -> None:
        self.name = name
        self.attributes: dict[str, Any] = (
            dict(attributes or {})
        )
        self.links: list[SpanLink] = (
            list(links or [])
        )
        self.events: list[
            tuple[str, dict[str, str] | None]
        ] = []
        self.exceptions: list[BaseException] = []
        self.started_at = time.monotonic()
        self.ended_at: float | None = None
        self.status_ok = True

    def set_attribute(
        self,
        key: str,
        value: str | int | float | bool,
    ) -> None:
        self.attributes[str(key)] = value

    def add_event(
        self,
        name: str,
        attributes: (
            dict[str, str] | None
        ) = None,
    ) -> None:
        self.events.append(
            (name, dict(attributes) if attributes else None)
        )

    def record_exception(
        self, exc: BaseException
    ) -> None:
        self.exceptions.append(exc)
        self.status_ok = False

    def carrier(self) -> TraceCarrier | None:
        version = "00"
        trace_id = "0" * 32
        span_id = hex(id(self))[2:].zfill(16)[:16]
        flags = "01"
        return TraceCarrier(
            traceparent=f"{version}-{trace_id}-{span_id}-{flags}"
        )

    def __enter__(self) -> "InMemorySpan":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.ended_at = time.monotonic()
        if exc is not None:
            self.record_exception(exc)
            self.status_ok = False
        return False


class InMemoryTelemetry(TelemetryPort):
    def __init__(
        self,
        *,
        validate_attributes: bool = True,
    ) -> None:
        self.validate_attributes = validate_attributes
        self._lock = threading.Lock()
        self.spans: list[InMemorySpan] = []
        self.metrics: list[MetricPoint] = []

    def clear(self) -> None:
        with self._lock:
            self.spans.clear()
            self.metrics.clear()

    @contextmanager
    def span(
        self,
        name: str,
        *,
        attributes: (
            dict[str, Any] | None
        ) = None,
        links: list[SpanLink] | None = None,
    ):
        span = InMemorySpan(name, attributes, links)
        try:
            with self._lock:
                self.spans.append(span)
            yield span
        finally:
            span.__exit__(None, None, None)

    def counter(
        self,
        name: str,
        value: int,
        attributes: dict[str, str],
    ) -> None:
        if self.validate_attributes:
            validate_metric_attributes(
                name, attributes
            )
        point = MetricPoint(
            kind="counter",
            name=name,
            value=float(value),
            attributes=dict(attributes),
        )
        with self._lock:
            self.metrics.append(point)

    def histogram(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        if self.validate_attributes:
            validate_metric_attributes(
                name, attributes
            )
        point = MetricPoint(
            kind="histogram",
            name=name,
            value=float(value),
            attributes=dict(attributes),
        )
        with self._lock:
            self.metrics.append(point)

    def gauge(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        if self.validate_attributes:
            validate_metric_attributes(
                name, attributes
            )
        point = MetricPoint(
            kind="gauge",
            name=name,
            value=float(value),
            attributes=dict(attributes),
        )
        with self._lock:
            self.metrics.append(point)
