"""Phase 28 OpenTelemetry adapter（延迟初始化，缺库时退回 NoOp）。"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from app.observability.ports import SpanPort, TelemetryPort
from app.observability.redaction import sanitize_error_message
from app.observability.schemas import (
    SpanLink,
    TraceCarrier,
)

_otel_error_logger = logging.getLogger(
    "otel_error"
)


class OTelSpan(SpanPort):
    def __init__(self, wrapped: Any) -> None:
        self._span = wrapped

    def set_attribute(
        self,
        key: str,
        value: str | int | float | bool,
    ) -> None:
        try:
            self._span.set_attribute(key, value)
        except Exception as err:
            _otel_error_logger.warning(
                "otel set_attribute failed: %s",
                sanitize_error_message(str(err)),
            )

    def add_event(
        self,
        name: str,
        attributes: (
            dict[str, str] | None
        ) = None,
    ) -> None:
        try:
            self._span.add_event(
                name=name,
                attributes=dict(attributes or {}),
            )
        except Exception as err:
            _otel_error_logger.warning(
                "otel add_event failed: %s",
                sanitize_error_message(str(err)),
            )

    def record_exception(
        self, exc: BaseException
    ) -> None:
        try:
            self._span.record_exception(exc)
            self._span.set_status(
                _SPAN_STATUS_CODE_ERROR
                if _SPAN_STATUS_CODE_ERROR is not None
                else 2,
                sanitize_error_message(str(exc)),
            )
        except Exception as err:
            _otel_error_logger.warning(
                "otel record_exception failed: %s",
                sanitize_error_message(str(err)),
            )

    def carrier(self) -> TraceCarrier | None:
        return _inject_carrier_from_span(
            self._span
        )


def _inject_carrier_from_span(
    span: Any,
) -> TraceCarrier | None:
    if (
        _TRACE_PROPAGATOR is None
        or _TRACE is None
        or _SPAN_CONTEXT is None
    ):
        return None
    try:
        ctx = _TRACE.set_span_in_context(span)
        carrier: dict[str, str] = {}
        _TRACE_PROPAGATOR.inject(carrier, context=ctx)
        traceparent = carrier.get("traceparent")
        if not traceparent:
            return None
        return TraceCarrier(
            traceparent=traceparent,
            tracestate=carrier.get("tracestate") or None,
        )
    except Exception:
        return None


def _extract_links_as_otel(
    links: list[SpanLink] | None,
) -> list[Any] | None:
    if not links or _OTEL_LINK is None or _SPAN_CONTEXT is None:
        return None
    out: list[Any] = []
    for link in links:
        try:
            ctx = _TRACE_PROPAGATOR.extract(
                {
                    "traceparent": link.carrier.traceparent,
                    **(
                        {"tracestate": link.carrier.tracestate}
                        if link.carrier.tracestate
                        else {}
                    ),
                }
            ) if _TRACE_PROPAGATOR else None
            if ctx is None:
                continue
            span_ctx = _SPAN_CONTEXT.from_context(ctx) if hasattr(_SPAN_CONTEXT, "from_context") else None
            if span_ctx is None:
                continue
            out.append(
                _OTEL_LINK(
                    context=span_ctx,
                    attributes=dict(link.attributes),
                )
            )
        except Exception:
            continue
    return out or None


# ---- 延迟初始化：OTel 可选依赖 ----

_TRACE = None
_TRACER_PROVIDER = None
_TRACE_PROPAGATOR = None
_SPAN_CONTEXT = None
_OTEL_LINK = None
_SPAN_STATUS_CODE_ERROR = None
_METER = None
_METER_COUNTERS: dict[str, Any] = {}
_METER_HISTOGRAMS: dict[str, Any] = {}
_OTEL_INITIALIZED = False


def _ensure_otel_initialized(
    *,
    service_name: str,
    service_version: str,
    environment: str,
    otlp_http_endpoint: str | None,
    trace_enabled: bool,
    metric_enabled: bool,
) -> None:
    global _TRACE, _TRACER_PROVIDER, _TRACE_PROPAGATOR, _SPAN_CONTEXT
    global _OTEL_LINK, _SPAN_STATUS_CODE_ERROR, _METER, _OTEL_INITIALIZED
    if _OTEL_INITIALIZED:
        return
    _OTEL_INITIALIZED = True
    try:
        from opentelemetry import (
            trace as _t,
            metrics as _m,
        )
        from opentelemetry.trace import (
            Link as _L,
            SpanContext,
            StatusCode,
        )
        from opentelemetry.propagate import (
            get_global_textmap,
        )

        _TRACE = _t
        _SPAN_CONTEXT = SpanContext
        _OTEL_LINK = _L
        _SPAN_STATUS_CODE_ERROR = StatusCode.ERROR
        _TRACE_PROPAGATOR = get_global_textmap()

        if trace_enabled:
            try:
                from opentelemetry.sdk.trace import (
                    TracerProvider,
                )
                from opentelemetry.sdk.resources import (
                    Resource,
                )
                from opentelemetry.sdk.trace.export import (
                    BatchSpanProcessor,
                )
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                resource = Resource.create(
                    {
                        "service.name": service_name,
                        "service.version": service_version,
                        "deployment.environment": environment,
                    }
                )
                provider = TracerProvider(
                    resource=resource
                )
                if otlp_http_endpoint:
                    provider.add_span_processor(
                        BatchSpanProcessor(
                            OTLPSpanExporter(
                                endpoint=f"{otlp_http_endpoint.rstrip('/')}/v1/traces"
                            )
                        )
                    )
                _t.set_tracer_provider(provider)
                _TRACER_PROVIDER = provider
            except Exception as err:
                _otel_error_logger.warning(
                    "otel trace init failed: %s",
                    sanitize_error_message(str(err)),
                )

        if metric_enabled:
            try:
                from opentelemetry.sdk.metrics import (
                    MeterProvider,
                )
                from opentelemetry.sdk.resources import (
                    Resource as _R,
                )
                from opentelemetry.sdk.metrics.export import (
                    PeriodicExportingMetricReader,
                )
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                    OTLPMetricExporter,
                )

                resource = _R.create(
                    {
                        "service.name": service_name,
                        "service.version": service_version,
                        "deployment.environment": environment,
                    }
                )
                readers = []
                if otlp_http_endpoint:
                    reader = PeriodicExportingMetricReader(
                        OTLPMetricExporter(
                            endpoint=f"{otlp_http_endpoint.rstrip('/')}/v1/metrics"
                        ),
                        export_interval_millis=15_000,
                    )
                    readers.append(reader)
                mp = MeterProvider(
                    resource=resource,
                    metric_readers=readers,
                )
                _m.set_meter_provider(mp)
                _METER = mp.get_meter(
                    service_name, version=service_version
                )
            except Exception as err:
                _otel_error_logger.warning(
                    "otel metric init failed: %s",
                    sanitize_error_message(str(err)),
                )
    except Exception as err:
        _otel_error_logger.warning(
            "otel SDK unavailable: %s",
            sanitize_error_message(str(err)),
        )


class OTelTelemetry(TelemetryPort):
    def __init__(
        self,
        *,
        service_name: str,
        service_version: str,
        environment: str,
        otlp_http_endpoint: str | None,
        trace_enabled: bool = True,
        metric_enabled: bool = True,
    ) -> None:
        _ensure_otel_initialized(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
            otlp_http_endpoint=otlp_http_endpoint,
            trace_enabled=trace_enabled,
            metric_enabled=metric_enabled,
        )
        self._service_name = service_name
        self._tracer = (
            _TRACE.get_tracer(
                service_name, service_version
            )
            if _TRACE is not None
            else None
        )

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
        if self._tracer is None:
            from app.observability.noop import (
                NoOpSpan,
            )

            yield NoOpSpan()
            return
        otel_links = _extract_links_as_otel(links)
        wrapped = self._tracer.start_span(
            name=name,
            attributes=dict(attributes or {}),
            links=otel_links,
        )
        span = OTelSpan(wrapped)
        try:
            with wrapped:
                yield span
        except Exception as exc:
            span.record_exception(exc)
            raise

    def counter(
        self,
        name: str,
        value: int,
        attributes: dict[str, str],
    ) -> None:
        if _METER is None:
            return
        try:
            inst = _METER_COUNTERS.get(name)
            if inst is None:
                inst = _METER.create_counter(name)
                _METER_COUNTERS[name] = inst
            inst.add(value, attributes or {})
        except Exception as err:
            _otel_error_logger.warning(
                "otel counter %s failed: %s",
                name,
                sanitize_error_message(str(err)),
            )

    def histogram(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        if _METER is None:
            return
        try:
            inst = _METER_HISTOGRAMS.get(name)
            if inst is None:
                inst = _METER.create_histogram(
                    name, unit="s"
                )
                _METER_HISTOGRAMS[name] = inst
            inst.record(value, attributes or {})
        except Exception as err:
            _otel_error_logger.warning(
                "otel histogram %s failed: %s",
                name,
                sanitize_error_message(str(err)),
            )

    def gauge(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        # OTel 异步 gauge 在 Python sdk 需要 callback，这里做 fail-open 降级。
        _otel_error_logger.debug(
            "gauge %s=%.3f attributes=%s",
            name,
            value,
            attributes,
        )
