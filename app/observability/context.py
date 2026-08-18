from __future__ import annotations

"""Phase 28 使用 contextvars 绑定执行上下文。

contextvars 能跨 async task 正常传播，但新线程通常需要显式复制/重新 bind。
Worker heartbeat 线程只绑定 worker/session，不应误继承某个 Job 的上下文。
"""


import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from app.observability.schemas import TelemetryContext

_current_context: ContextVar[TelemetryContext] = (
    ContextVar(
        "paper_copilot_telemetry_context",
        default=TelemetryContext(),
    )
)


def short_secret_hash(
    value: str | None,
) -> str | None:
    if not value:
        return None
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:16]


def current_telemetry_context() -> TelemetryContext:
    # 返回不可与 ContextVar 内对象共享可变状态的新模型。
    return _current_context.get().model_copy(deep=True)


@contextmanager
def bind_telemetry_context(
    **updates: str | None,
) -> Iterator[TelemetryContext]:
    previous = _current_context.get()
    merged = previous.model_copy(
        update={
            key: value
            for key, value in updates.items()
            if value is not None
        }
    )
    token = _current_context.set(merged)
    try:
        yield merged
    finally:
        _current_context.reset(token)
