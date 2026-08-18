from __future__ import annotations

"""Phase 28 便于业务重复使用的小工具。

- metric 只允许使用低基数允许列表。
- 异常对象先过 sanitize_error_message() 再写入 span 或 log。
"""


from typing import Any

from app.observability.ports import (
    SpanPort,
    TelemetryPort,
)
from app.observability.redaction import redact, sanitize_error_message


def record_span_exception_safe(
    span: SpanPort,
    exc: BaseException,
    *,
    attributes: (
        dict[str, str] | None
    ) = None,
) -> None:
    span.record_exception(exc)
    cleaned = sanitize_error_message(str(exc))
    span.add_event(
        "exception.summary",
        attributes={
            "message": cleaned[:800],
            **(attributes or {}),
        },
    )


def increment_counter_safe(
    telemetry: TelemetryPort,
    name: str,
    *,
    value: int = 1,
    attributes: dict[str, str],
) -> None:
    try:
        telemetry.counter(
            name, value=value, attributes=attributes
        )
    except Exception:
        # 业务不应因 metric 登记失败而失败。
        pass


def redact_span_event_payload(
    payload: Any,
) -> dict[str, str]:
    cleaned = redact(payload, max_chars=1000)
    if isinstance(cleaned, dict):
        return {
            str(key): str(val)[:256]
            for key, val in cleaned.items()
        }
    return {"detail": str(cleaned)[:1000]}
