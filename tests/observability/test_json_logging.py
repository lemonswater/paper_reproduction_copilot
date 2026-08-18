from __future__ import annotations

import io
import json
import logging
import os

import pytest

from app.observability.context import bind_telemetry_context
from app.observability.json_logging import (
    JsonLogFormatter,
    configure_structured_logging,
    get_log_level_from_env,
)


def _capture_log_output(logger_name: str = "test_json_logger"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    return logger, buffer, handler


def test_formatter_produces_json():
    logger, buffer, _ = _capture_log_output("test_produces_json")
    logger.info("hello")
    output = buffer.getvalue().strip()
    assert output
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"
    assert "timestamp" in parsed


def test_formatter_injects_context():
    logger, buffer, _ = _capture_log_output("test_injects_context")
    with bind_telemetry_context(request_id="REQ-1", job_id="JOB-1"):
        logger.warning("x")
    output = buffer.getvalue().strip()
    parsed = json.loads(output)
    assert parsed["request_id"] == "REQ-1"
    assert parsed["job_id"] == "JOB-1"
    assert parsed["message"] == "x"


def test_formatter_redacts_secrets():
    logger, buffer, _ = _capture_log_output("test_redacts_secrets")
    with bind_telemetry_context(request_id="x"):
        logger.error(
            "msg with authorization:Bearer XXX and api_key=secret123",
            extra={"extra": {"api_key": "secret"}},
        )
    output = buffer.getvalue().strip()
    parsed = json.loads(output)
    msg_str = parsed["message"]
    assert "Bearer XXX" not in msg_str or "api_key" not in str(parsed.get("extra", {}))
    extra = parsed.get("extra")
    if extra is not None and isinstance(extra, dict):
        assert extra.get("api_key") == "<redacted>"


def test_formatter_handles_exception():
    logger, buffer, _ = _capture_log_output("test_handles_exception")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("boom")
    output = buffer.getvalue().strip()
    parsed = json.loads(output)
    has_exc_type = parsed.get("exc_type") == "ZeroDivisionError"
    has_exc_field = bool(parsed.get("exc"))
    assert has_exc_type or has_exc_field
    if "exc" in parsed:
        assert len(parsed["exc"]) <= 8000 + 100


def test_configure_structured_logging():
    configure_structured_logging(level=logging.WARNING)
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    found = False
    for h in root.handlers:
        if isinstance(h.formatter, JsonLogFormatter):
            found = True
            break
    assert found, "root logger 至少有一个 handler 使用 JsonLogFormatter"


def test_get_log_level_from_env():
    original = os.environ.get("LOG_LEVEL")
    try:
        if "LOG_LEVEL" in os.environ:
            del os.environ["LOG_LEVEL"]
        assert get_log_level_from_env() == logging.INFO

        os.environ["LOG_LEVEL"] = "DEBUG"
        assert get_log_level_from_env() == logging.DEBUG

        os.environ["LOG_LEVEL"] = "not_a_real_level"
        assert get_log_level_from_env() == logging.INFO
    finally:
        if original is None:
            if "LOG_LEVEL" in os.environ:
                del os.environ["LOG_LEVEL"]
        else:
            os.environ["LOG_LEVEL"] = original
