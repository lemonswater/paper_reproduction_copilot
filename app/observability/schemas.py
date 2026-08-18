"""Phase 28 telemetry 数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class TelemetryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceCarrier(TelemetryModel):
    """允许跨数据库边界持久化的最小 W3C carrier。"""

    traceparent: str = Field(
        min_length=55, max_length=512
    )
    tracestate: str | None = Field(
        default=None, max_length=512
    )

    @field_validator("traceparent")
    @classmethod
    def validate_traceparent(cls, value: str) -> str:
        # 详细语义仍由 OTel propagator 解析，这里先拒绝换行和明显注入。
        if "\n" in value or "\r" in value:
            raise ValueError("traceparent 不能包含换行")
        return value.strip()


class TelemetryContext(TelemetryModel):
    request_id: str | None = None
    job_id: str | None = None
    run_id: str | None = None
    thread_id: str | None = None
    worker_id: str | None = None
    worker_session_id: str | None = None
    worker_host_id: str | None = None
    claim_token_hash: str | None = None
    graph_node: str | None = None
    stage: str | None = None
    execution_backend: str | None = None
    container_id: str | None = None


class MetricPoint(TelemetryModel):
    kind: Literal["counter", "histogram", "gauge"]
    name: str
    value: float
    attributes: dict[str, str] = Field(
        default_factory=dict
    )


class SpanLink(TelemetryModel):
    carrier: TraceCarrier
    attributes: dict[str, str] = Field(
        default_factory=dict
    )


class ReadinessCheck(TelemetryModel):
    name: str
    status: Literal["ready", "degraded", "not_ready"]
    latency_seconds: float = Field(ge=0)
    detail: str | None = None


class ReadinessReport(TelemetryModel):
    status: Literal["ready", "degraded", "not_ready"]
    component: Literal["api", "worker"]
    checks: list[ReadinessCheck]
    generated_at: str
