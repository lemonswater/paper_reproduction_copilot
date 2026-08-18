from __future__ import annotations

import asyncio
import threading

import pytest

from app.mcp_export.call_executor import McpExportCallExecutor
from app.mcp_export.errors import (
    McpExportBusy,
    McpExportTimedOut,
)
from app.observability.in_memory import InMemoryTelemetry


@pytest.fixture
def anyio_backend() -> str:
    # McpExportCallExecutor 使用 asyncio.run_in_executor。
    return "asyncio"


class BrokenTelemetry:
    def span(self, *args, **kwargs):
        raise RuntimeError("span backend unavailable")

    def counter(self, *args, **kwargs):
        raise RuntimeError("metric backend unavailable")

    def histogram(self, *args, **kwargs):
        raise RuntimeError("metric backend unavailable")

    def gauge(self, *args, **kwargs):
        raise RuntimeError("metric backend unavailable")


@pytest.mark.anyio
async def test_executor_returns_sync_result() -> None:
    executor = McpExportCallExecutor(
        workers=1,
        queue_capacity=0,
        timeout_seconds=1,
        telemetry=InMemoryTelemetry(validate_attributes=True),
    )
    try:
        result = await executor.run(
            operation="get_reproduction_status",
            request_id="request-1",
            job_id="job_" + "1" * 32,
            function=lambda value: value + 1,
            function_kwargs={"value": 2},
        )
    finally:
        executor.close()
    assert result == 3


@pytest.mark.anyio
async def test_telemetry_failure_does_not_change_business_result() -> None:
    executor = McpExportCallExecutor(
        workers=1,
        queue_capacity=0,
        timeout_seconds=1,
        telemetry=BrokenTelemetry(),
    )
    try:
        result = await executor.run(
            operation="get_reproduction_status",
            request_id="request-telemetry-failure",
            job_id="job_" + "4" * 32,
            function=lambda: "business-ok",
        )
    finally:
        executor.close()
    assert result == "business-ok"


@pytest.mark.anyio
async def test_timeout_keeps_slot_until_real_thread_finishes() -> None:
    release = threading.Event()
    started = threading.Event()

    def block() -> str:
        started.set()
        release.wait(timeout=2)
        return "released"

    executor = McpExportCallExecutor(
        workers=1,
        queue_capacity=0,
        timeout_seconds=0.05,
        telemetry=InMemoryTelemetry(validate_attributes=True),
    )
    try:
        with pytest.raises(McpExportTimedOut):
            await executor.run(
                operation="get_reproduction_status",
                request_id="request-timeout",
                job_id="job_" + "2" * 32,
                function=block,
            )
        assert started.is_set()

        # wait_for 已超时，但 block 所在线程还没退出，slot 不能提前复用。
        with pytest.raises(McpExportBusy):
            await executor.run(
                operation="get_reproduction_status",
                request_id="request-busy",
                job_id="job_" + "2" * 32,
                function=lambda: "must-not-run",
            )

        release.set()
        result = None
        for _ in range(50):
            await asyncio.sleep(0.01)
            try:
                result = await executor.run(
                    operation="get_reproduction_status",
                    request_id="request-after-release",
                    job_id="job_" + "2" * 32,
                    function=lambda: "ok",
                )
                break
            except McpExportBusy:
                continue
        assert result == "ok"
    finally:
        release.set()
        executor.close()


@pytest.mark.anyio
async def test_closed_executor_rejects_new_work() -> None:
    executor = McpExportCallExecutor(
        workers=1,
        queue_capacity=1,
        timeout_seconds=1,
        telemetry=InMemoryTelemetry(validate_attributes=True),
    )
    executor.close()
    with pytest.raises(McpExportBusy):
        await executor.run(
            operation="get_reproduction_status",
            request_id="request-closed",
            job_id="job_" + "3" * 32,
            function=lambda: "never",
        )
