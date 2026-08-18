from __future__ import annotations

import pytest

from app.observability.in_memory import (
    InMemoryTelemetry,
    validate_metric_attributes,
    ALLOWED_METRIC_ATTRIBUTES,
)


def test_spans_recorded():
    tel = InMemoryTelemetry()
    with tel.span("a") as s:
        s.set_attribute("k", 1)
        s.add_event("e1")
    assert len(tel.spans) == 1
    span = tel.spans[0]
    assert span.name == "a"
    assert span.attributes["k"] == 1
    assert len(span.events) == 1
    assert span.events[0][0] == "e1"


def test_span_carrier_returns_tracecarrier():
    tel = InMemoryTelemetry()
    with tel.span("test-carrier") as s:
        carrier = s.carrier()
    assert carrier is not None
    assert isinstance(carrier.traceparent, str)
    assert len(carrier.traceparent) > 0
    assert carrier.traceparent.startswith("00-")
    assert len(carrier.traceparent) >= 55


def test_span_exception_recorded():
    from app.observability.in_memory import InMemorySpan
    span = InMemorySpan("a", {}, [])
    try:
        with span:
            raise ValueError("x")
    except ValueError:
        pass
    assert len(span.exceptions) == 1
    assert span.status_ok is False


def test_counter_records_point():
    tel = InMemoryTelemetry()
    tel.counter(
        "paper_copilot_http_requests_total",
        2,
        {"method": "GET", "route": "/x", "status_class": "2xx"},
    )
    assert len(tel.metrics) == 1
    point = tel.metrics[0]
    assert point.value == 2
    assert point.kind == "counter"
    assert point.name == "paper_copilot_http_requests_total"


def test_histogram_and_gauge():
    tel = InMemoryTelemetry()
    tel.histogram(
        "paper_copilot_http_request_duration_seconds",
        0.123,
        {"method": "GET", "route": "/x", "status_class": "2xx"},
    )
    assert len(tel.metrics) == 1
    assert tel.metrics[0].kind == "histogram"
    assert tel.metrics[0].value == 0.123

    tel.gauge(
        "paper_copilot_http_request_duration_seconds",
        0.456,
        {"method": "GET", "route": "/x", "status_class": "2xx"},
    )
    assert len(tel.metrics) == 2
    assert tel.metrics[1].kind == "gauge"
    assert tel.metrics[1].value == 0.456


def test_validate_rejects_unknown_metric():
    with pytest.raises(ValueError, match="metric 未登记"):
        validate_metric_attributes("bogus_metric", {})


def test_validate_rejects_extra_attributes():
    with pytest.raises(ValueError, match="未登记属性"):
        validate_metric_attributes(
            "paper_copilot_http_requests_total",
            {"method": "GET", "route": "/x", "status_class": "2xx", "extra": "x"},
        )


def test_validate_rejects_forbidden(monkeypatch):
    import app.observability.in_memory as im_module
    fake_allowed = dict(ALLOWED_METRIC_ATTRIBUTES.copy())
    fake_allowed["test_metric_with_forbidden"] = frozenset({"job_id", "outcome"})
    monkeypatch.setattr(im_module, "ALLOWED_METRIC_ATTRIBUTES", fake_allowed)
    with pytest.raises(ValueError, match="高基数或敏感身份"):
        validate_metric_attributes(
            "test_metric_with_forbidden",
            {"outcome": "ok", "job_id": "x"},
        )


def test_counter_safe_validate_skipped():
    tel = InMemoryTelemetry(validate_attributes=False)
    tel.counter("whatever", 1, {"job_id": "a"})
    assert len(tel.metrics) == 1
    assert tel.metrics[0].name == "whatever"


def test_clear_resets_spans_and_metrics():
    tel = InMemoryTelemetry()
    with tel.span("a"):
        pass
    tel.counter(
        "paper_copilot_http_requests_total",
        1,
        {"method": "GET", "route": "/x", "status_class": "2xx"},
    )
    assert len(tel.spans) == 1
    assert len(tel.metrics) == 1
    tel.clear()
    assert tel.spans == []
    assert tel.metrics == []
