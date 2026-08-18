from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.observability.schemas import (
    TraceCarrier,
    TelemetryContext,
    MetricPoint,
    SpanLink,
    ReadinessCheck,
    ReadinessReport,
)


def test_tracecarrier_valid():
    valid = "00" + "a" * 32 + "-" + "b" * 16 + "-02"
    carrier = TraceCarrier(traceparent=f"  {valid}  ")
    assert carrier.traceparent == valid


def test_tracecarrier_rejects_newline():
    with pytest.raises(ValueError):
        TraceCarrier(traceparent="00" + "a" * 32 + "-" + "b" * 16 + "-02\n")


def test_tracecarrier_rejects_short():
    with pytest.raises(ValidationError):
        TraceCarrier(traceparent="short")


def test_telemetry_context_defaults():
    ctx = TelemetryContext()
    assert ctx.request_id is None
    assert ctx.job_id is None
    assert ctx.run_id is None
    assert ctx.thread_id is None
    assert ctx.worker_id is None
    assert ctx.worker_session_id is None
    assert ctx.worker_host_id is None
    assert ctx.claim_token_hash is None
    assert ctx.graph_node is None
    assert ctx.stage is None
    assert ctx.execution_backend is None
    assert ctx.container_id is None


def test_telemetry_context_bind():
    ctx = TelemetryContext(request_id="a", job_id="b")
    dumped = ctx.model_dump()
    assert dumped["request_id"] == "a"
    assert dumped["job_id"] == "b"


def test_metric_point_counter():
    mp = MetricPoint(kind="counter", name="a", value=1, attributes={})
    assert mp.kind == "counter"
    assert mp.name == "a"
    assert mp.value == 1
    assert mp.attributes == {}


def test_metric_point_rejects_extra():
    with pytest.raises(ValidationError):
        MetricPoint(kind="counter", name="a", value=1, extra="x")


def test_span_link_roundtrip():
    traceparent = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
    link = SpanLink(
        carrier=TraceCarrier(traceparent=traceparent),
        attributes={"k": "v"},
    )
    dumped = link.model_dump()
    assert dumped["carrier"]["traceparent"] == traceparent
    assert dumped["attributes"] == {"k": "v"}


def test_readiness_report():
    report = ReadinessReport(
        status="ready",
        component="api",
        checks=[],
        generated_at="2024-01-01T00:00:00Z",
    )
    assert report.status == "ready"
    assert report.component == "api"
    assert report.checks == []
    assert report.generated_at == "2024-01-01T00:00:00Z"


def test_readiness_checks_validation():
    with pytest.raises(ValidationError):
        ReadinessCheck(
            name="db",
            status="broken",
            latency_seconds=0.1,
        )
