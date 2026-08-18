from __future__ import annotations

import logging

import pytest

from app.observability.noop import NoOpSpan, NoOpTelemetry
from app.observability.runtime import (
    SERVICE_NAME,
    build_telemetry_runtime,
    configure_runtime_logging,
)


def test_noop_span_is_pass_through():
    span = NoOpSpan()
    span.set_attribute("x", 1)
    span.set_attribute("y", "value")
    span.set_attribute("z", True)
    span.set_attribute("w", 1.5)
    span.add_event("event1")
    span.add_event("event2", {"k": "v"})
    span.record_exception(ValueError("test"))
    with span as s:
        assert s is span


def test_noop_span_carrier_is_none():
    span = NoOpSpan()
    assert span.carrier() is None


def test_noop_telemetry_context_works():
    tel = NoOpTelemetry()
    with tel.span("a", attributes={}) as s:
        s.set_attribute("x", 1)
        s.add_event("e")
    tel.counter("name", 1, {})
    tel.histogram("name2", 1.0, {})
    tel.gauge("name3", 2.0, {})


def test_build_runtime_noop_backend():
    runtime = build_telemetry_runtime(backend="noop")
    assert runtime.backend == "noop"
    assert isinstance(runtime.telemetry, NoOpTelemetry)


def test_build_runtime_in_memory():
    runtime = build_telemetry_runtime(backend="in_memory")
    assert runtime.backend == "in_memory"
    from app.observability.in_memory import InMemoryTelemetry
    assert isinstance(runtime.telemetry, InMemoryTelemetry)


def test_build_runtime_unknown():
    with pytest.raises(ValueError, match="未知 observability backend"):
        build_telemetry_runtime(backend="nonsense")


def test_service_name_exists():
    assert isinstance(SERVICE_NAME, str)
    assert len(SERVICE_NAME) > 0


def test_configure_runtime_logging_smoke():
    level1 = configure_runtime_logging()
    assert isinstance(level1, int)
    level2 = configure_runtime_logging()
    assert isinstance(level2, int)
    assert logging.getLogger().level == level2
