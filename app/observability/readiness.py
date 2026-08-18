from __future__ import annotations

"""Phase 28 Readiness。

把 provider 调用排除在 readiness 之外：
Provider 在 API/Worker 里都可能被临时限流或网络抖动，
若 readiness 依赖它会导致"没有新请求→自愈机会更少"的正反馈。
"""


import logging
import threading
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal

from app.observability.schemas import (
    ReadinessCheck,
    ReadinessReport,
)

log = logging.getLogger(__name__)

ReadinessStatus = Literal[
    "ready", "degraded", "not_ready"
]


@dataclass
class ReadinessProbe:
    name: str
    is_critical: bool
    check: Callable[[], ReadinessStatus]
    timeout_seconds: float = 2.0


class ReadinessService:
    def __init__(
        self,
        component: Literal["api", "worker"],
        probes: list[ReadinessProbe],
        *,
        max_workers: int = 4,
    ) -> None:
        self.component = component
        self.probes = list(probes)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="readiness",
        )
        self._lock = threading.Lock()
        self._last_report: ReadinessReport | None = (
            None
        )
        self._last_report_at: float | None = None
        self._cache_ttl_seconds = 1.0

    def cached_report(self) -> ReadinessReport:
        with self._lock:
            import time as _t

            now = _t.monotonic()
            if (
                self._last_report is not None
                and self._last_report_at is not None
                and now - self._last_report_at
                < self._cache_ttl_seconds
            ):
                return self._last_report
        report = self.check()
        with self._lock:
            self._last_report = report
            self._last_report_at = _t.monotonic()
        return report

    def check(self) -> ReadinessReport:
        results: list[ReadinessCheck] = []
        critical_failed = False
        degraded = False
        futures = {
            self._executor.submit(
                self._run_one, probe
            ): probe
            for probe in self.probes
        }
        for fut, probe in futures.items():
            try:
                status, latency = fut.result(
                    timeout=probe.timeout_seconds
                    + 0.5
                )
                detail = None
            except FutureTimeoutError:
                status = (
                    "not_ready"
                    if probe.is_critical
                    else "degraded"
                )
                latency = probe.timeout_seconds
                detail = "timeout"
            except Exception as err:
                status = (
                    "not_ready"
                    if probe.is_critical
                    else "degraded"
                )
                latency = probe.timeout_seconds
                detail = str(err)[:200]
                log.warning(
                    "readiness probe %s error: %s",
                    probe.name,
                    detail,
                )
            if status == "not_ready":
                if probe.is_critical:
                    critical_failed = True
                else:
                    degraded = True
            elif status == "degraded":
                degraded = True
            results.append(
                ReadinessCheck(
                    name=probe.name,
                    status=status,
                    latency_seconds=float(latency),
                    detail=detail,
                )
            )
        overall: ReadinessStatus = (
            "not_ready"
            if critical_failed
            else "degraded" if degraded else "ready"
        )
        return ReadinessReport(
            status=overall,
            component=self.component,
            checks=sorted(
                results, key=lambda r: r.name
            ),
            generated_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

    @staticmethod
    def _run_one(
        probe: ReadinessProbe,
    ) -> tuple[ReadinessStatus, float]:
        import time as _t

        started = _t.monotonic()
        try:
            status = probe.check()
        except Exception:
            raise
        latency = max(
            0.0, _t.monotonic() - started
        )
        if status not in {"ready", "degraded", "not_ready"}:
            status = "degraded"
        return status, latency  # type: ignore[return-value]


def build_liveness_probe() -> bool:
    """liveness 只检查本进程在运行，避免依赖任何外部系统。"""

    return True
