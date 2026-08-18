"""Phase 28 NoOp adapter，避免单元测试导入 OTel。"""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import Any, Literal

from app.observability.ports import SpanPort, TelemetryPort
from app.observability.schemas import (
    SpanLink,
    TraceCarrier,
)


class NoOpSpan(SpanPort):
    def set_attribute(
        self,
        key: str,
        value: str | int | float | bool,
    ) -> None:
        return None

    def add_event(
        self,
        name: str,
        attributes: (
            dict[str, str] | None
        ) = None,
    ) -> None:
        return None

    def record_exception(
        self, exc: BaseException
    ) -> None:
        return None

    def carrier(self) -> TraceCarrier | None:
        return None

    def __enter__(self) -> "NoOpSpan":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> Literal[False]:
        return False


class NoOpTelemetry(TelemetryPort):
    def __init__(self) -> None:
        self.default_span = NoOpSpan()

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
        yield self.default_span

    def counter(
        self,
        name: str,
        value: int,
        attributes: dict[str, str],
    ) -> None:
        return None

    def histogram(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        return None

    def gauge(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        return None
