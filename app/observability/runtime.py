"""Phase 28 Telemetry Runtime：根据 settings 选择后端，避免业务到处 if-else。"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.observability.in_memory import InMemoryTelemetry
from app.observability.json_logging import (
    configure_structured_logging,
    get_log_level_from_env,
)
from app.observability.noop import NoOpTelemetry
from app.observability.ports import TelemetryPort


SERVICE_NAME = "paper-copilot"
SERVICE_VERSION = "0.1.0"


@dataclass
class TelemetryRuntime:
    telemetry: TelemetryPort
    backend: str


def build_telemetry_runtime(
    *,
    backend: str | None = None,
    otlp_http_endpoint: str | None = None,
    environment: str | None = None,
) -> TelemetryRuntime:
    chosen_backend = backend or settings.observability_backend
    if chosen_backend == "noop":
        return TelemetryRuntime(
            telemetry=NoOpTelemetry(), backend=chosen_backend
        )
    if chosen_backend == "in_memory":
        return TelemetryRuntime(
            telemetry=InMemoryTelemetry(
                validate_attributes=True
            ),
            backend=chosen_backend,
        )
    if chosen_backend == "otel":
        from app.observability.otel_adapter import (
            OTelTelemetry,
        )

        return TelemetryRuntime(
            telemetry=OTelTelemetry(
                service_name=SERVICE_NAME,
                service_version=SERVICE_VERSION,
                environment=environment
                or settings.telemetry_environment,
                otlp_http_endpoint=otlp_http_endpoint
                or settings.otlp_http_endpoint,
                trace_enabled=settings.otel_trace_enabled,
                metric_enabled=settings.otel_metric_enabled,
            ),
            backend=chosen_backend,
        )
    raise ValueError(
        f"未知 observability backend：{chosen_backend}"
    )


def configure_runtime_logging() -> int:
    level = get_log_level_from_env()
    configure_structured_logging(level=level)
    return level
