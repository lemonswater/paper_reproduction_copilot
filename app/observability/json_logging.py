from __future__ import annotations

"""Phase 28 统一 JSON 日志。

- 所有 handler 共享同一个 Formatter。
- 不要把 token/job_id 这种高基数/敏感字段直接当 metric label，
  这里会把它们放进 structured log，而不是 Prometheus counter。
"""


import json
import logging
import os
import sys
from datetime import datetime, timezone

from app.observability.context import current_telemetry_context
from app.observability.redaction import redact


class JsonLogFormatter(logging.Formatter):
    def format(
        self, record: logging.LogRecord
    ) -> str:
        context = (
            current_telemetry_context().model_dump(
                exclude_none=True
            )
        )
        payload: dict[str, object] = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **context,
        }
        if record.exc_info:
            payload["exc_type"] = (
                record.exc_info[0].__name__
                if record.exc_info[0]
                else None
            )
            payload["exc"] = self.formatException(
                record.exc_info
            )[:8000]
        if record.name == "otel_error":
            payload["otel_internal"] = True
        return json.dumps(
            redact(payload),
            ensure_ascii=False,
            sort_keys=True,
        )


def configure_structured_logging(
    *,
    level: int | str = logging.INFO,
    stream=None,
) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler(
        stream or sys.stderr
    )
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    # 关掉第三方库的 debug 噪音（但仍记录 WARNING+）。
    for noisy in (
        "httpx",
        "urllib3",
        "opentelemetry",
    ):
        logging.getLogger(noisy).setLevel(
            logging.WARNING
        )


def get_log_level_from_env() -> int:
    raw = (
        os.getenv("LOG_LEVEL", "INFO")
        .strip()
        .upper()
    )
    return getattr(logging, raw, logging.INFO)
