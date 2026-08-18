from __future__ import annotations

import io
import json
import logging
import time

import pytest

from app.observability.in_memory import (
    ALLOWED_METRIC_ATTRIBUTES,
    InMemoryTelemetry,
    validate_metric_attributes,
)
from app.observability.context import (
    bind_telemetry_context,
    current_telemetry_context,
    short_secret_hash,
)
from app.observability.schemas import (
    ReadinessReport,
    SpanLink,
    TraceCarrier,
)
from app.observability.json_logging import (
    JsonLogFormatter,
    configure_structured_logging,
)
from app.observability.readiness import (
    ReadinessProbe,
    ReadinessService,
)
from app.observability.redaction import redact


def test_structured_log_includes_telemetry_context():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("test_ctx_inline_1")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    with bind_telemetry_context(
        request_id="R1", job_id="J1", worker_id="W1"
    ):
        logger.info("hello world")

    output = stream.getvalue().strip()
    assert output, "log output should not be empty"
    parsed = json.loads(output)
    assert parsed["request_id"] == "R1"
    assert parsed["job_id"] == "J1"
    assert parsed["worker_id"] == "W1"
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"


def test_structured_log_redacts_secrets_in_context():
    sensitive_dict = {
        "extra_field": {
            "api_key": "SECRET-ABC-789",
            "nested": {"authorization": "Bearer TOKEN-XYZ-456"},
        },
        "normal": "keep-me",
    }
    redacted = redact(sensitive_dict)
    assert redacted["extra_field"]["api_key"] == "<redacted>"
    assert (
        redacted["extra_field"]["nested"]["authorization"]
        == "<redacted>"
    )
    assert redacted["normal"] == "keep-me"
    raw_redacted_str = json.dumps(redacted)
    assert "<redacted>" in raw_redacted_str
    assert "SECRET-ABC-789" not in raw_redacted_str
    assert "TOKEN-XYZ-456" not in raw_redacted_str

    pure_url = (
        "https://user:pass@api.example.com/v1?api_key=SECRET-IN-URL-123"
    )
    sanitized_url = redact(pure_url)
    assert isinstance(sanitized_url, str)
    assert "SECRET-IN-URL-123" not in sanitized_url
    assert "user:pass@" not in sanitized_url
    assert "api.example.com" in sanitized_url

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("test_redact_inline_2")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    url_msg = (
        "https://user:secret-pass@host.example.com:8080/api?key=HIDDEN-VALUE-999"
    )
    logger.info(url_msg)
    output = stream.getvalue().strip()
    parsed = json.loads(output)
    assert "HIDDEN-VALUE-999" not in output
    assert "user:secret-pass@" not in output
    assert "host.example.com" in parsed["message"]
    assert parsed["level"] == "INFO"

    payload_for_log = {
        "type": "request",
        "Authorization": "Bearer SK-LIVE-SECRET-000",
        "data": {"api_key": "PROVIDER-KEY-555", "input": "text"},
    }
    redacted_payload = redact(payload_for_log)
    assert redacted_payload["type"] == "request"
    assert redacted_payload["Authorization"] == "<redacted>"
    assert redacted_payload["data"]["api_key"] == "<redacted>"
    assert redacted_payload["data"]["input"] == "text"
    serialized_redacted = json.dumps(redacted_payload)
    assert "<redacted>" in serialized_redacted
    assert "SK-LIVE-SECRET-000" not in serialized_redacted
    assert "PROVIDER-KEY-555" not in serialized_redacted


def test_inmemory_span_links_roundtrip_via_carrier():
    telem_a = InMemoryTelemetry()
    with telem_a.span("submit") as span_a:
        carrier_a = span_a.carrier()
        assert carrier_a is not None
        assert isinstance(carrier_a, TraceCarrier)
        tp_a = carrier_a.traceparent
        assert len(tp_a) >= 55

    link = SpanLink(carrier=carrier_a)

    telem_b = InMemoryTelemetry()
    with telem_b.span(
        "execute",
        links=[SpanLink(carrier=carrier_a)],
    ) as span_b:
        assert span_b is not None

    assert len(telem_b.spans) == 1
    span_b_recorded = telem_b.spans[0]
    assert len(span_b_recorded.links) >= 1
    roundtripped_carrier = span_b_recorded.links[0].carrier
    assert roundtripped_carrier.traceparent == tp_a
    assert roundtripped_carrier.traceparent == carrier_a.traceparent


def test_claim_count_metric_uses_allowed_attributes_only():
    telem = InMemoryTelemetry(validate_attributes=True)
    telem.counter(
        "paper_copilot_jobs_claim_total",
        1,
        {"outcome": "claimed"},
    )
    assert len(telem.metrics) == 1
    assert telem.metrics[0].attributes["outcome"] == "claimed"

    with pytest.raises(ValueError):
        telem.counter(
            "paper_copilot_jobs_claim_total",
            1,
            {"outcome": "claimed", "job_id": "J1"},
        )

    with pytest.raises(ValueError):
        validate_metric_attributes(
            "paper_copilot_jobs_claim_total",
            {"outcome": "ok", "run_id": "R"},
        )


def test_worker_like_claim_scenario_increments_counters():
    telem = InMemoryTelemetry(validate_attributes=False)

    telem.counter(
        "paper_copilot_jobs_claim_total",
        1,
        {"outcome": "claimed"},
    )
    telem.histogram(
        "paper_copilot_job_execution_duration_seconds",
        1.23,
        {
            "outcome": "succeeded",
            "execution_backend": "local",
        },
    )
    telem.counter(
        "paper_copilot_workers_registered_total",
        1,
        {"backend": "local"},
    )

    assert len(telem.metrics) == 3

    claim_counter = [
        m for m in telem.metrics if m.name == "paper_copilot_jobs_claim_total"
    ][0]
    assert claim_counter.kind == "counter"
    assert claim_counter.value == 1.0
    assert claim_counter.attributes == {"outcome": "claimed"}

    duration_hist = [
        m
        for m in telem.metrics
        if m.name == "paper_copilot_job_execution_duration_seconds"
    ][0]
    assert duration_hist.kind == "histogram"
    assert duration_hist.value == 1.23
    assert duration_hist.attributes == {
        "outcome": "succeeded",
        "execution_backend": "local",
    }

    worker_reg = [
        m
        for m in telem.metrics
        if m.name == "paper_copilot_workers_registered_total"
    ][0]
    assert worker_reg.kind == "counter"
    assert worker_reg.value == 1.0
    assert worker_reg.attributes == {"backend": "local"}

    claim_attrs = set(
        ALLOWED_METRIC_ATTRIBUTES["paper_copilot_jobs_claim_total"]
    )
    assert "outcome" in claim_attrs
    assert "job_id" not in claim_attrs

    exec_attrs = set(
        ALLOWED_METRIC_ATTRIBUTES[
            "paper_copilot_job_execution_duration_seconds"
        ]
    )
    assert "outcome" in exec_attrs
    assert "execution_backend" in exec_attrs

    worker_attrs = set(
        ALLOWED_METRIC_ATTRIBUTES["paper_copilot_workers_registered_total"]
    )
    assert "backend" in worker_attrs


def test_readiness_with_mixed_probes_and_timeout():
    def critical_ready() -> str:
        return "ready"

    def noncritical_degraded() -> str:
        return "degraded"

    def noncritical_slow() -> str:
        time.sleep(3.0)
        return "ready"

    probes = [
        ReadinessProbe(
            name="critical_db",
            is_critical=True,
            check=critical_ready,
            timeout_seconds=2.0,
        ),
        ReadinessProbe(
            name="degraded_cache",
            is_critical=False,
            check=noncritical_degraded,
            timeout_seconds=2.0,
        ),
        ReadinessProbe(
            name="slow_network",
            is_critical=False,
            check=noncritical_slow,
            timeout_seconds=0.01,
        ),
    ]

    service = ReadinessService(component="worker", probes=probes)
    report = service.check()

    assert isinstance(report, ReadinessReport)
    assert report.component == "worker"
    assert report.status == "degraded"
    assert len(report.checks) == 3

    check_by_name = {c.name: c for c in report.checks}

    assert check_by_name["critical_db"].status == "ready"
    assert check_by_name["critical_db"].latency_seconds >= 0

    assert check_by_name["degraded_cache"].status == "degraded"
    assert check_by_name["degraded_cache"].latency_seconds >= 0

    slow_check = check_by_name["slow_network"]
    assert slow_check.status == "degraded"
    assert slow_check.detail == "timeout"
    assert slow_check.latency_seconds >= 0


def test_secret_hash_is_consistent_and_not_plaintext():
    claim_token = "secret-long-token-value-123"
    hash1 = short_secret_hash(claim_token)
    hash2 = short_secret_hash(claim_token)

    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) == 16
    assert hash1 != claim_token
    assert "secret" not in hash1
    assert "token" not in hash1
    assert "123" not in hash1

    hash_a = short_secret_hash("a")
    hash_b = short_secret_hash("b")
    assert hash_a != hash_b
    assert len(hash_a) == 16
    assert len(hash_b) == 16

    assert short_secret_hash(None) is None
    assert short_secret_hash("") is None


def test_claim_token_hash_in_context_bind():
    plaintext_token = "MY-SECRET-CLAIM-TOKEN-VALUE-987654"
    hash_val = short_secret_hash(plaintext_token)
    assert hash_val is not None
    assert len(hash_val) == 16

    with bind_telemetry_context(
        job_id="J",
        run_id="R",
        claim_token_hash=hash_val,
    ):
        ctx = current_telemetry_context()
        assert ctx.claim_token_hash == hash_val
        assert ctx.job_id == "J"
        assert ctx.run_id == "R"
        assert len(ctx.claim_token_hash) == 16
        assert ctx.claim_token_hash != plaintext_token

        dumped = ctx.model_dump()
        dumped_str = json.dumps(dumped)
        assert plaintext_token not in dumped_str
        assert "MY-SECRET-CLAIM" not in dumped_str
        assert "987654" not in dumped_str
        assert hash_val in dumped_str
