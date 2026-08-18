from __future__ import annotations

"""Phase 28 Telemetry 业务端口。

业务模块必须依赖此端口，不要直接在每个 node 中初始化 OTel SDK。
"""


from contextlib import AbstractContextManager
from typing import Any, Protocol

from app.observability.schemas import (
    SpanLink,
    TraceCarrier,
)


class SpanPort(Protocol):
    def set_attribute(
        self,
        key: str,
        value: str | int | float | bool,
    ) -> None:
        ...

    def add_event(
        self,
        name: str,
        attributes: (
            dict[str, str] | None
        ) = None,
    ) -> None:
        ...

    def record_exception(
        self, exc: BaseException
    ) -> None:
        ...

    def carrier(self) -> TraceCarrier | None:
        ...


class TelemetryPort(Protocol):
    def span(
        self,
        name: str,
        *,
        attributes: (
            dict[str, Any] | None
        ) = None,
        links: list[SpanLink] | None = None,
    ) -> AbstractContextManager[SpanPort]:
        ...

    def counter(
        self,
        name: str,
        value: int,
        attributes: dict[str, str],
    ) -> None:
        ...

    def histogram(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        ...

    def gauge(
        self,
        name: str,
        value: float,
        attributes: dict[str, str],
    ) -> None:
        ...
