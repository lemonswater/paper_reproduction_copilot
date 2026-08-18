from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from functools import partial
from time import perf_counter
from typing import TypeVar

from app.mcp_export.errors import (
    McpExportBusy,
    McpExportTimedOut,
)
from app.observability.context import short_secret_hash
from app.observability.instrumentation import (
    increment_counter_safe,
    record_span_exception_safe,
)
from app.observability.noop import NoOpSpan
from app.observability.ports import TelemetryPort


ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class McpExportServerContext:
    """MCPServer lifespan 向每个 handler 提供的受控运行资源。"""

    calls: "McpExportCallExecutor"


@contextmanager
def _safe_span(
    telemetry: TelemetryPort,
    *,
    attributes: dict[str, str],
):
    """Span 后端完全失败时退回 NoOp，不改变业务结果。"""

    manager = None
    span = NoOpSpan()
    try:
        manager = telemetry.span(
            "mcp.export.invoke",
            attributes=attributes,
        )
        span = manager.__enter__()
    except Exception:
        manager = None

    try:
        yield span
    finally:
        if manager is not None:
            try:
                manager.__exit__(*sys.exc_info())
            except Exception:
                pass


class McpExportCallExecutor:
    """用独立线程池执行同步 Service，并限制 worker 与等待队列。"""

    def __init__(
        self,
        *,
        workers: int,
        queue_capacity: int,
        timeout_seconds: float,
        telemetry: TelemetryPort,
    ) -> None:
        if workers < 1:
            raise ValueError("workers must be positive")
        if queue_capacity < 0:
            raise ValueError("queue_capacity must not be negative")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.timeout_seconds = timeout_seconds
        self.telemetry = telemetry
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="mcp-export-call",
        )
        # slot 数量等于正在执行的 worker 加允许等待的有限 queue。
        self._slots = threading.BoundedSemaphore(
            workers + queue_capacity
        )
        self._state_lock = threading.Lock()
        self._closed = False

    def _is_closed(self) -> bool:
        with self._state_lock:
            return self._closed

    def close(self) -> None:
        """停止接收新任务；不在线程内强杀已经运行的 Python 代码。"""

        with self._state_lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(
            wait=False,
            cancel_futures=True,
        )

    def _record_metric(
        self,
        *,
        operation: str,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        attributes = {
            "operation": operation,
            "outcome": outcome,
        }
        increment_counter_safe(
            self.telemetry,
            "paper_copilot_mcp_export_calls_total",
            attributes=attributes,
        )
        try:
            self.telemetry.histogram(
                "paper_copilot_mcp_export_duration_seconds",
                value=duration_seconds,
                attributes=attributes,
            )
        except Exception:
            # Telemetry 失败不能改变 MCP 业务结果。
            pass

    async def run(
        self,
        *,
        operation: str,
        request_id: str,
        job_id: str,
        function: Callable[..., ResultT],
        function_kwargs: dict[str, object] | None = None,
    ) -> ResultT:
        if self._is_closed():
            raise McpExportBusy("MCP Export executor is closed")

        acquired = self._slots.acquire(blocking=False)
        if not acquired:
            self._record_metric(
                operation=operation,
                outcome="busy",
                duration_seconds=0.0,
            )
            raise McpExportBusy("MCP Export executor queue is full")

        started = perf_counter()
        outcome = "succeeded"
        loop = asyncio.get_running_loop()

        kwargs = function_kwargs or {}
        try:
            future = loop.run_in_executor(
                self._executor,
                partial(function, **kwargs),
            )
        except Exception:
            self._slots.release()
            raise

        # wait_for 超时只停止等待。slot 必须在真实 Future 结束后释放，
        # 否则超时线程仍在运行时新任务会突破容量边界。
        def release_slot(completed) -> None:
            self._slots.release()
            if completed.cancelled():
                return
            try:
                # 超时后也读取晚到异常，避免 un-retrieved Future 警告。
                completed.exception()
            except Exception:
                pass

        future.add_done_callback(release_slot)

        span_attributes = {
            "mcp.operation": operation,
            "mcp.request_id_hash": short_secret_hash(request_id) or "none",
            "mcp.job_id_hash": short_secret_hash(job_id) or "none",
        }
        with _safe_span(
            self.telemetry,
            attributes=span_attributes,
        ) as span:
            try:
                return await asyncio.wait_for(
                    asyncio.shield(future),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                outcome = "timeout"
                try:
                    record_span_exception_safe(
                        span,
                        exc,
                        attributes={
                            "error_code": "MCP_EXPORT_TIMEOUT"
                        },
                    )
                except Exception:
                    pass
                raise McpExportTimedOut(
                    "MCP Export handler deadline exceeded"
                ) from None
            except asyncio.CancelledError:
                outcome = "cancelled"
                try:
                    span.add_event(
                        "mcp.export.cancelled",
                        attributes={"operation": operation},
                    )
                except Exception:
                    pass
                raise
            except Exception as exc:
                outcome = "failed"
                try:
                    record_span_exception_safe(span, exc)
                except Exception:
                    pass
                raise
            finally:
                duration = max(0.0, perf_counter() - started)
                try:
                    span.set_attribute("mcp.outcome", outcome)
                    span.set_attribute(
                        "mcp.duration_seconds",
                        duration,
                    )
                except Exception:
                    pass
                self._record_metric(
                    operation=operation,
                    outcome=outcome,
                    duration_seconds=duration,
                )


def build_mcp_export_lifespan(
    *,
    workers: int,
    queue_capacity: int,
    timeout_seconds: float,
    telemetry: TelemetryPort,
):
    """返回 MCPServer 所需的 async lifespan callback。"""

    @asynccontextmanager
    async def lifespan(_server) -> AsyncIterator[McpExportServerContext]:
        calls = McpExportCallExecutor(
            workers=workers,
            queue_capacity=queue_capacity,
            timeout_seconds=timeout_seconds,
            telemetry=telemetry,
        )
        try:
            yield McpExportServerContext(calls=calls)
        finally:
            calls.close()

    return lifespan
